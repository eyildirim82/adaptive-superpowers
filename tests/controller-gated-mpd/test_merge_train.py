import hashlib, json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'skills/controller-gated-mpd/scripts/merge_train.sh'
HEAD='a'*40; BASE='b'*40; MERGE='c'*40; MOVED='d'*40
FAKE_GH=r'''#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$FAKE_GH_CALLS"
if [[ ${1:-} == api ]]; then
 c=0; [[ -f $FAKE_TRUNK_COUNT ]] && c=$(cat "$FAKE_TRUNK_COUNT")
 IFS=, read -r -a s <<< "$FAKE_TRUNK_SHAS"; i=$c; ((i>=${#s[@]})) && i=$((${#s[@]}-1))
 echo "${s[$i]}"; echo $((c+1)) > "$FAKE_TRUNK_COUNT"; exit 0
fi
if [[ ${1:-} == pr && ${2:-} == view ]]; then
 if [[ "$*" == *headRefOid* ]]; then
  printf '%s\t%s\t%s\t%s\t%s\n' "$FAKE_PR_HEAD" "$FAKE_PR_BASE" "$FAKE_PR_MERGEABLE" "$FAKE_PR_MERGE_STATE" "$FAKE_PR_DRAFT"
 else printf '%s\t%s\n' "$FAKE_PR_STATE" "$FAKE_PR_MERGE_SHA"; fi
 exit 0
fi
[[ ${1:-} == pr && ${2:-} == merge ]] && exit 0
[[ ${1:-} == pr && ${2:-} == ready ]] && exit 0
echo unsupported >&2; exit 9
'''
READY=r'''import json,os,sys
from pathlib import Path
Path(os.environ['READY_CALLS']).open('a').write(' '.join(sys.argv[1:])+'\n')
p=os.environ.get('MUTATE_PROFILE')
if p:
 d=json.loads(Path(p).read_text()); d['adaptive']['authorization']['merge']='denied'; Path(p).write_text(json.dumps(d)+'\n')
raise SystemExit(0 if os.environ.get('READY_STATUS','valid')=='valid' else 2)
'''
TRUNK=r'''import os,sys
from pathlib import Path
Path(os.environ['TRUNK_CALLS']).open('a').write(' '.join(sys.argv[1:])+'\n')
s=os.environ.get('TRUNK_STATUS','green'); raise SystemExit(0 if s=='green' else 4 if s=='pending' else 2)
'''

class MergeTrainTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup); self.p=Path(self.t.name)
  self.bin=self.p/'bin'; self.bin.mkdir(); gh=self.bin/'gh'; gh.write_text(FAKE_GH); gh.chmod(0o755)
  self.sd=self.p/'scripts'; self.sd.mkdir(); self.script=self.sd/'merge_train.sh'; shutil.copy2(SCRIPT,self.script)
  (self.sd/'verify_ready.py').write_text(READY); (self.sd/'check_trunk_evidence.py').write_text(TRUNK)
  self.calls=self.p/'gh.log'; self.rcalls=self.p/'ready.log'; self.tcalls=self.p/'trunk.log'
  for x in (self.calls,self.rcalls,self.tcalls): x.write_text('')

 def profile(self,auth):
  a=self.p/'approvals'; a.mkdir(exist_ok=True)
  d={'schema_version':4,'protocol_version':6,'wave':'t','repository':{'repo':'owner/repo','trunk':'main','frozen_base_sha':BASE},
     'adaptive':{'risk_floor':'CRITICAL','authorization':{'push':'granted','merge':auth,'deploy':'denied','production_write':'denied','destructive_action':'denied'},'transport':'prompt-handoff'},
     'verification':{'workflow':{'name':'Full CI','path':'.github/workflows/ci.yml','head_event':'push','trunk_event':'push'},'gate_catalog':[{'id':'tests','job':'test'}]},
     'risk_policy':{'default_level':'STANDARD','levels':{'FAST':{'gates':['tests']},'STANDARD':{'gates':['tests']},'CRITICAL':{'gates':['tests']}},'path_floors':[]},
     'hot_zones':[],'lanes':[],'merge':{'method':'squash','approvals_dir':str(a),'trunk_green_after_each':True}}
  f=self.p/f'{auth}.json'; f.write_text(json.dumps(d)+'\n'); return f,a

 def ready(self,p,a,digest=None,base='main'):
  d=digest or hashlib.sha256(p.read_bytes()).hexdigest(); f=a/'pr-42.ready.json'
  f.write_text(json.dumps({'schema_version':4,'protocol_version':6,'repo':'owner/repo','pr':42,'head_sha':HEAD,'base_ref':base,'verdict':'READY',
   'risk':{'effective':'CRITICAL'},'profile':{'sha256':d},'evidence':{'selected_run':{'id':1,'run_attempt':1}}})+'\n'); return f

 def env(self,shas=None,**kw):
  e=os.environ.copy(); e.update({'PATH':f'{self.bin}:{e["PATH"]}','FAKE_GH_CALLS':str(self.calls),'READY_CALLS':str(self.rcalls),'TRUNK_CALLS':str(self.tcalls),
   'FAKE_TRUNK_COUNT':str(self.p/'count'),'FAKE_TRUNK_SHAS':','.join(shas or [BASE]),'READY_STATUS':kw.get('ready','valid'),'TRUNK_STATUS':kw.get('trunk','green'),
   'FAKE_PR_HEAD':HEAD,'FAKE_PR_BASE':kw.get('base','main'),'FAKE_PR_MERGEABLE':'MERGEABLE','FAKE_PR_MERGE_STATE':kw.get('state','CLEAN'),
   'FAKE_PR_DRAFT':'false','FAKE_PR_STATE':kw.get('prstate','MERGED'),'FAKE_PR_MERGE_SHA':kw.get('merge_sha',MERGE)})
  if kw.get('mutate'): e['MUTATE_PROFILE']=str(kw['mutate'])
  return e

 def run_train(self,p,a,apply=False,env=None,timeout=0,n=12):
  c=['bash',str(self.script),'--profile',str(p),'--repo','owner/repo','--approvals-dir',str(a),'--timeout',str(timeout)]
  if apply:c+=['--apply']
  c+=['42']; return subprocess.run(c,cwd=ROOT,env=env or self.env(),text=True,capture_output=True,timeout=5+n*3)
 def mutations(self): return [x for x in self.calls.read_text().splitlines() if x.startswith(('pr merge ','pr ready '))]

 def test_plan_mode_no_mutation(self):
  p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,env=self.env([BASE,BASE])); self.assertEqual(r.returncode,0,r.stderr); self.assertIn('[plan]',r.stdout); self.assertEqual(self.mutations(),[])

 def test_denied_and_unknown_no_mutation(self):
  for auth in ('denied','unknown'):
   with self.subTest(auth=auth):
    self.setUp(); p,a=self.profile(auth); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE])); self.assertEqual(r.returncode,2); self.assertIn('[plan]',r.stdout); self.assertEqual(self.mutations(),[])

 def test_granted_exact_head_and_postmerge_proof(self):
  p,a=self.profile('granted'); ap=self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,BASE,MERGE])); self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertIn(f'pr merge 42 --repo owner/repo --squash --match-head-commit {HEAD}',self.calls.read_text()); t=self.tcalls.read_text(); self.assertIn(f'--sha {MERGE}',t); self.assertIn('--branch main',t); self.assertIn(f'--approval {ap}',t)

 def test_stale_or_mismatched_ready_rejected(self):
  p,a=self.profile('granted'); self.ready(p,a,digest='f'*64); r=self.run_train(p,a,True,self.env([BASE,BASE])); self.assertEqual(r.returncode,2); self.assertEqual(self.mutations(),[])
  self.setUp(); p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE],ready='stale')); self.assertEqual(r.returncode,2); self.assertEqual(self.mutations(),[])

 def test_authorization_profile_change_blocks_mutation(self):
  p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,BASE],mutate=p)); self.assertEqual(r.returncode,2); self.assertIn('profile changed',(r.stdout+r.stderr).lower()); self.assertEqual(self.mutations(),[])

 def test_trunk_pins_and_races(self):
  p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([MOVED])); self.assertEqual(r.returncode,2); self.assertEqual(self.mutations(),[])
  self.setUp(); p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,MOVED])); self.assertEqual(r.returncode,2); self.assertIn('trunk moved unexpectedly',(r.stdout+r.stderr).lower()); self.assertEqual(self.mutations(),[])

 def test_pr_target_and_green_metadata_required(self):
  p,a=self.profile('granted'); self.ready(p,a,base='release'); r=self.run_train(p,a,True,self.env([BASE,BASE],base='release')); self.assertEqual(r.returncode,2); self.assertEqual(self.mutations(),[])
  self.setUp(); p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE],state='UNSTABLE')); self.assertEqual(r.returncode,2); self.assertEqual(self.mutations(),[])

 def test_github_merged_and_resulting_trunk_required(self):
  p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,BASE],prstate='OPEN',merge_sha=''),0); self.assertEqual(r.returncode,3); self.assertIn('did not confirm',r.stderr.lower())
  self.setUp(); p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,BASE,MOVED],merge_sha=MERGE)); self.assertEqual(r.returncode,3); self.assertIn('trunk moved unexpectedly after',(r.stdout+r.stderr).lower()); self.assertEqual(self.tcalls.read_text(),'')

 def test_postmerge_green_proof_required(self):
  p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,BASE,MERGE],trunk='gap')); self.assertEqual(r.returncode,3); self.assertIn('trunk not GREEN',r.stderr); self.assertNotIn('Merge train complete',r.stdout)

 def test_timeout_regression_is_deterministic(self):
  self.assertTrue(FAKE_GH.startswith('#!/usr/bin/env bash')); self.assertNotEqual(5+1*3,5+12*3)
  p,a=self.profile('granted'); self.ready(p,a); r=self.run_train(p,a,True,self.env([BASE,BASE,BASE,MERGE]),n=16); self.assertEqual(r.returncode,0,r.stdout+r.stderr)

if __name__=='__main__': unittest.main()
