"""Developer oracle: one JSON object per stdin line, one canonical result per line.
Not the PCG network framing or a production server. Python 3.10+, stdlib only.
"""
from pathlib import Path
import sys,json
from .common import PCGError,canonical,digest,parse_json,hero_id_from_uid
from .battle import new_match,apply_action,project_view,legal_commands
from .player import claim_hero,select_login_snapshot,game_day
from .nfc_storage import encode_container,decode_container
from .wire import fragment,decode_frame
ROOT=Path(__file__).resolve().parents[1]
PACK=json.loads((ROOT/'content/core_pack.json').read_text(encoding='utf8'))
def dispatch(req):
 op=req['op'];a=req.get('args',{});pack=req.get('pack',PACK)
 if op=='canonical':return {'canonical_utf8_hex':canonical(a['value']).hex(),'sha256':digest(a['value'])}
 if op=='new_match':
  s=new_match(pack,**a);return {'state':s,'state_hash':digest(s)}
 if op=='action':
  r=apply_action(pack,a['state'],a['actor'],a['command']);return {**r,'state_hash':digest(r['state'])}
 if op=='view':
  v=project_view(a['state'],a['viewer']);return {'view':v,'view_hash':digest(v)}
 if op=='legal_commands':return legal_commands(pack,a['state'],a['actor'],a['action_id'])
 if op=='claim':return claim_hero(a['snapshot'],a['hero'],pack,a['observed_utc_ms'],a['clock_source'],a['device_id'],a['new_snapshot_id'])
 if op=='login_select':return select_login_snapshot(**a)
 if op=='game_day':return {'day_id':game_day(a['utc_ms'])}
 if op=='hero_uid':return {'hero_card_id':hero_id_from_uid(a['technology'],a['uid_hex'])}
 if op=='encode_card':return {'container_hex':encode_container(**a).hex()}
 if op=='decode_card':return decode_container(bytes.fromhex(a['container_hex']),a.get('expected_profile'))
 if op=='fragment':return {'frames_hex':[f.hex() for f in fragment(bytes.fromhex(a['envelope_hex']),a['link_id'],a['transfer_id'],a.get('mtu',128))]}
 if op=='decode_frame':
  f=decode_frame(bytes.fromhex(a['frame_hex']),a.get('mtu',128));f['payload_hex']=f.pop('payload').hex();return f
 raise PCGError('ORACLE_OPERATION_UNSUPPORTED',op)
def main():
 for line in sys.stdin.buffer:
  if not line.strip():continue
  try:result={'ok':True,'result':dispatch(parse_json(line,max_bytes=262144))}
  except PCGError as e:result={'ok':False,'error_code':e.code,'detail':e.detail}
  except (KeyError,TypeError,ValueError) as e:result={'ok':False,'error_code':'ORACLE_INVALID_ARGUMENT','detail':str(e)}
  sys.stdout.buffer.write(canonical(result)+b'\n');sys.stdout.buffer.flush()
if __name__=='__main__':main()
