"""Pure core/claim contract tests. Does not claim real hardware coverage."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,unittest
from reference.common import PCGError,canonical,digest,parse_json,parse_canonical,hero_id_from_uid
from reference.battle import new_match,apply_action,project_view,board_scores,legal_commands,Authority,validate_pack
from reference.player import claim_hero,game_day,select_login_snapshot,redeem_ink_skin,validate_snapshot,bump_snapshot
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads((R/p).read_text())
PACK=load('content/core_pack.json');DECK=PACK['starter_deck'];DRAW=load('fixtures/draw_vectors.json');BASE=DRAW['initial_snapshot'];NOW=DRAW['utc_ms'];DEV=DRAW['device_id'];HERO=load('examples/hero_blind_box.json');FIXED=load('examples/hero_fixed.json')
def sid(n):return f'40000000-0000-4000-8000-{n:012d}'
def state(seed=0):return new_match(PACK,'test_match',['player_a','player_b'],[DECK,DECK],seed)
def command(s,a,kind='pass',idx=None,row=None,target=None,aid=None):return {'match_id':s['match_id'],'action_id':aid or f'action_{s["revision"]}_{a}','expected_revision':s['revision'],'kind':kind,'card_instance_id':None if idx is None else f'p{a}:{idx:02d}','row':row,'target_instance_id':target}
def move(s,a,idx=None,row=None,target=None):return apply_action(PACK,s,a,command(s,a,'pass' if idx is None else 'play',idx,row,target))['state']
def claim(base=BASE,hero=HERO,now=NOW,n=1):return claim_hero(base,hero,PACK,now,'network',DEV,sid(n))
class Errors(unittest.TestCase):
 def err(self,code,fn,*args,**kw):
  with self.assertRaises(PCGError) as e:fn(*args,**kw)
  self.assertEqual(e.exception.code,code)
class CanonicalTests(Errors):
 def test_golden(self):
  for v in load('fixtures/canonical_vectors.json')['valid']:
   self.assertEqual(canonical(v['value']).hex(),v['canonical_utf8_hex']);self.assertEqual(digest(v['value']),v['sha256'])
 def test_invalid(self):
  for h in load('fixtures/canonical_vectors.json')['invalid_hex']:
   with self.assertRaises(PCGError):parse_canonical(bytes.fromhex(h))
 def test_manual_bytes_and_numbers(self):
  self.assertEqual(canonical({'b':2,'a':'卡/\n'}),b'{"a":"'+ '卡'.encode()+b'/\\n","b":2}')
  self.assertEqual(digest({}),hashlib.sha256(b'{}').hexdigest())
  self.err('JSON_INTEGER_RANGE',canonical,{'x':9007199254740992});self.err('JSON_TYPE',canonical,{'x':1.0})
 def test_keys_unicode_and_duplicate(self):
  self.err('JSON_KEY',canonical,{'中文':1});self.err('JSON_KEY',canonical,{'\n':1});self.err('JSON_INVALID_UNICODE',canonical,{'x':'\ud800'})
  self.err('JSON_DUPLICATE_KEY',parse_json,b'{"x":1,"x":2}');self.err('JSON_TOO_LARGE',parse_json,b'{}',1)
 def test_uid_case_and_order(self):
  v=DRAW['uid_vector'];self.assertEqual(hero_id_from_uid(v['technology'],v['uid_hex'].lower()),v['hero_card_id']);self.assertNotEqual(hero_id_from_uid('nfc-a','0102'),hero_id_from_uid('nfc-a','0201'))
class BattleTests(Errors):
 def test_initial_and_invalid_decks(self):
  s=state(1);self.assertEqual(s['turn_player'],1);self.assertEqual([len(p['hand']) for p in s['players']],[10,10]);self.assertEqual(board_scores(s),[0,0])
  self.err('DECK_SIZE_OR_DUPLICATE',new_match,PACK,'m',['a','b'],[DECK[:-1],DECK],0)
  self.err('DECK_SIZE_OR_DUPLICATE',new_match,PACK,'m',['a','b'],[[DECK[0]]*10,DECK],0)
 def test_invalid_actions_are_atomic(self):
  s=state();old=deepcopy(s);self.err('NOT_YOUR_TURN',apply_action,PACK,s,1,command(s,1));c=command(s,0);c['expected_revision']=1
  self.err('STALE_REVISION',apply_action,PACK,s,0,c);self.err('ILLEGAL_ROW',apply_action,PACK,s,0,command(s,0,'play',0,'rear'));self.assertEqual(s,old)
 def test_empty_target_unit_vs_tactic(self):
  s=state();self.err('NO_TACTIC_TARGET',apply_action,PACK,s,0,command(s,0,'play',8));s=move(s,0,5,'rear');self.assertEqual(board_scores(s),[3,0])
 def test_target_required_no_self_boost(self):
  s=move(state(),0,1,'front');s=move(s,1,0,'front')
  self.err('TARGET_REQUIRED_OR_INVALID',apply_action,PACK,s,0,command(s,0,'play',5,'rear'))
  self.err('TARGET_REQUIRED_OR_INVALID',apply_action,PACK,s,0,command(s,0,'play',5,'rear','p0:05'))
 def test_dial_order(self):
  s=move(state(),0,1,'front');s=move(s,1,1,'front');s=move(s,0,3,'rear');self.assertEqual(board_scores(s)[0],9)
  s=move(state(),0,3,'rear');s=move(s,1,1,'front');s=move(s,0,1,'front');self.assertEqual(board_scores(s)[0],7)
 def test_stable(self):
  s=move(state(),0,4,'rear');s=move(s,1,6,'rear','p0:04');s=move(s,0,5,'rear','p0:04');self.assertEqual(board_scores(s),[8,3]);self.assertEqual(s['players'][0]['board'][0]['power'],5)
 def test_shield_once(self):
  s=move(state(),0,7,'front');s=move(s,1,6,'rear','p0:07');self.assertFalse(s['players'][0]['board'][0]['shield']);s=move(s,0,1,'front');s=move(s,1,9,None,'p0:07');self.assertEqual(s['players'][0]['board'][0]['power'],2)
 def test_zero_stays_and_counts_other_row(self):
  s=move(state(),0,1,'front');s=move(s,1,6,'rear','p0:01');s=move(s,0,2,'rear');s=move(s,1,9,None,'p0:01');self.assertEqual(s['players'][0]['board'][0]['power'],0);s=move(s,0,3,'rear');self.assertEqual(s['players'][0]['board'][-1]['power'],5)
 def test_tactic_null_row_and_discard(self):
  s=move(state(),0,1,'front');s=move(s,1,1,'front');self.err('TACTIC_ROW',apply_action,PACK,s,0,command(s,0,'play',8,'front','p0:01'));s=move(s,0,8,None,'p0:01');self.assertEqual(s['players'][0]['played_count'],2);self.assertEqual(len(s['players'][0]['board']),1);self.assertEqual(len(s['players'][0]['discard']),1)
 def test_five_plays_auto_pass(self):
  s=move(state(),0,1,'front');s=move(s,1)
  for i,r,t in [(0,'front',None),(2,'rear',None),(3,'rear',None),(8,None,'p0:01')]:s=move(s,0,i,r,t)
  self.assertEqual(s['round_index'],2);self.assertEqual(len(s['players'][0]['hand']),5);self.assertEqual(len(s['players'][0]['discard']),5);self.assertEqual(s['turn_player'],0)
 def test_pass_permanent(self):
  s=move(state(),0);s=move(s,1,1,'front');self.assertEqual(s['turn_player'],1);self.err('NOT_YOUR_TURN',apply_action,PACK,s,0,command(s,0,'play',0,'front'));s=move(s,1);self.assertEqual(s['round_index'],2);self.assertFalse(s['players'][0]['passed'])
 def test_three_draws_and_starters(self):
  s=state();starters=[]
  for _ in range(3):
   starters.append(s['round_starter']);s=move(s,s['turn_player']);s=move(s,s['turn_player'])
  self.assertEqual(starters,[0,1,0]);self.assertEqual([p['match_points'] for p in s['players']],[3,3]);self.assertEqual(s['phase'],'finished');self.assertIsNone(s['winner'])
 def test_empty_rounds_auto_settle(self):
  s=state()
  for p in s['players']:p['discard']=p['hand'];p['hand']=[]
  s=move(s,0);self.assertEqual(len(s['round_results']),3);self.assertEqual(s['revision'],1);self.assertEqual(s['phase'],'finished')
 def test_real_twenty_plays_exhaust_hands_then_auto_draw(self):
  s=state()
  for idx,row in [(0,'front'),(1,'front'),(2,'rear'),(3,'rear'),(4,'rear')]:
   for _ in range(2):s=move(s,s['turn_player'],idx,row)
  self.assertEqual(s['round_index'],2)
  for idx,row in [(5,'rear'),(6,'rear'),(7,'front'),(8,None),(9,None)]:
   for _ in range(2):
    actor=s['turn_player']
    target=f'p{1-actor}:05' if idx==6 else (f'p{actor}:05' if idx==8 else (f'p{1-actor}:06' if idx==9 else None))
    s=move(s,actor,idx,row,target)
  self.assertEqual([r['scores'] for r in s['round_results']],[[24,24],[8,8],[0,0]])
  self.assertEqual([p['match_points'] for p in s['players']],[3,3]);self.assertEqual(s['revision'],20);self.assertEqual(s['phase'],'finished')
 def test_idempotence_accept_reject_conflict(self):
  a=Authority(PACK,state());c=command(a.state,0,'play',0,'front',aid='same');r=a.submit(0,c);self.assertEqual(a.submit(0,c),r);self.assertEqual(a.state['revision'],1);self.err('ACTION_ID_CONFLICT',a.submit,0,{**c,'row':'rear'})
  c=command(a.state,0,aid='rejected');r=a.submit(0,c);self.assertEqual(r['status'],'rejected');self.assertEqual(a.submit(0,c),r)
 def test_private_view(self):
  s=state();v=project_view(s,0);self.assertIn('hand',v['players'][0]);self.assertNotIn('hand',v['players'][1]);self.assertEqual(v['players'][1]['hand_count'],10);self.assertTrue(all('hand' not in p for p in project_view(s,None)['players']));self.assertIn('hand',s['players'][1])
 def test_full_golden_and_manual_totals(self):
  f=load('fixtures/battle_golden.json');s=new_match(PACK,**f['init']);self.assertEqual(digest(s),f['initial_state_hash'])
  for step in f['steps']:
   x=apply_action(PACK,s,step['actor'],step['command']);s=x['state'];self.assertEqual(s,step['expected_state']);self.assertEqual(digest(s),step['expected_state_hash']);self.assertEqual(x['events'],step['events']);self.assertEqual([digest(project_view(s,i)) for i in (0,1)],step['expected_view_hashes'])
  self.assertEqual([r['scores'] for r in s['round_results']],[[6,8],[8,6],[13,11]]);self.assertEqual([p['match_points'] for p in s['players']],[4,2]);self.assertEqual(s['winner'],0)
 def test_legal_enumerator_and_unknown_effect(self):
  s=state()
  for c in legal_commands(PACK,s,0,'candidate'):apply_action(PACK,s,0,c)
  self.assertEqual(s['revision'],0);p=deepcopy(PACK);p['cards'][0]['effect']['op']='REVIVE';self.err('CONTENT_UNSUPPORTED',validate_pack,p)
class PlayerTests(Errors):
 def test_draw_vectors(self):
  for v in DRAW['vectors']:
   x=claim_hero(v['input_snapshot'],v['hero'],PACK,v['observed_utc_ms'],v['clock_source'],DEV,v['new_snapshot_id']);self.assertEqual(x['reward'],v['expected_reward']);self.assertEqual(digest(x['snapshot']),v['expected_snapshot_hash'])
 def test_daily_duplicate_and_pool_change(self):
  s=claim()['snapshot'];p=deepcopy(PACK);p['draw_pools'][0]['pool_version']='1.0.1';self.err('ALREADY_CLAIMED_TODAY',claim_hero,s,HERO,p,NOW+1000,'network',DEV,sid(2));self.assertEqual(len(s['day_ledger']['claims']),1)
 def test_next_day_and_other_player(self):
  s=claim()['snapshot'];x=claim(s,now=NOW+86400000,n=2);self.assertEqual(x['reward']['day_id'],DRAW['game_day']+1);self.assertEqual(len(x['snapshot']['day_ledger']['claims']),1);b=deepcopy(BASE);b['player_id']='10000000-0000-4000-8000-000000000002';claim(b)
 def test_calendar_midnight_and_clock(self):
  boundary=DRAW['game_day']*86400000-28800000;self.assertEqual(game_day(boundary-1),DRAW['game_day']-1);self.assertEqual(game_day(boundary),DRAW['game_day']);self.err('TIME_UNAVAILABLE',game_day,12345);self.err('TIME_UNAVAILABLE',claim_hero,BASE,HERO,PACK,NOW,'unknown',DEV,sid(1));s=claim()['snapshot'];self.err('CLOCK_ROLLBACK',claim_hero,s,FIXED,PACK,NOW-86400000,'manual',DEV,sid(2))
 def test_deterministic_crash_retry(self):self.assertEqual(claim(n=1)['reward'],claim(n=2)['reward'])
 def test_duplicates_and_cosmetic(self):
  s=BASE
  for n in range(1,7):s=claim(s,FIXED,NOW+(n-1)*86400000,n)['snapshot']
  self.assertEqual(s['wallet']['shards'],50);self.assertEqual(s['collection'][0]['draw_count'],6);s=redeem_ink_skin(s,'paper_archive',PACK,DEV,sid(8),NOW+7*86400000);self.assertEqual(s['wallet']['shards'],0);self.assertEqual(s['collection'][0]['skin_id'],'ink');self.err('SKIN_ALREADY_OWNED',redeem_ink_skin,s,'paper_archive',PACK,DEV,sid(9),NOW+8*86400000)
 def test_unknown_nested_fields_preserved(self):
  b=deepcopy(BASE);b['future_root']={'v':1};b['clock']['future_clock']=True;b['day_ledger']['future_ledger']='keep';s=claim(b)['snapshot'];s=claim(s,now=NOW+86400000,n=2)['snapshot'];self.assertEqual(s['future_root'],{'v':1});self.assertTrue(s['clock']['future_clock']);self.assertEqual(s['day_ledger']['future_ledger'],'keep')
 def test_login_local_and_card_newer(self):
  s=claim()['snapshot'];x=select_login_snapshot(s,BASE);self.assertEqual(x['decision'],'local');self.assertFalse(x['write_card']);x=select_login_snapshot(BASE,s);self.assertEqual(x['decision'],'card');self.assertFalse(x['write_card']);self.assertEqual(select_login_snapshot(None,BASE)['decision'],'card')
 def test_branches_and_same_id_conflict(self):
  a=claim(n=1)['snapshot'];b=claim(hero=FIXED,n=2)['snapshot'];self.assertEqual(select_login_snapshot(a,b)['decision'],'conflict');b=deepcopy(a);b['wallet']['shards']=10;self.assertEqual(select_login_snapshot(a,b)['decision'],'conflict')
 def test_future_schema_read_only(self):
  f=deepcopy(BASE);f['save_schema_version']=2;self.assertEqual(select_login_snapshot(BASE,f)['decision'],'read_only');self.err('SAVE_SCHEMA_UNSUPPORTED',claim_hero,f,HERO,PACK,NOW,'network',DEV,sid(1));self.err('SAVE_SCHEMA_UNSUPPORTED',redeem_ink_skin,f,'paper_archive',PACK,DEV,sid(1),NOW);self.err('SAVE_SCHEMA_UNSUPPORTED',bump_snapshot,f,f,DEV,sid(1),NOW)
 def test_structural_validation(self):
  b=deepcopy(BASE);del b['collection'];self.err('SAVE_INVALID',validate_snapshot,b);b=deepcopy(BASE);b['nickname']='🎮'*32;self.err('SAVE_INVALID',validate_snapshot,b);self.err('SAVE_INVALID',validate_snapshot,[])
if __name__=='__main__':unittest.main()
