docker pull xingyaoww/sweb.eval.x86_64.astropy_s_astropy-12907:latest
reset
export SANDBOX_PERSIST_SANDBOX=1
export model_config=llm.gemini_pro
export model_config=llm.gemini
export model_config=$1
echo $model_config
export USE_HINT_TEXT=false

git_version=HEAD
agent=CodeActAgent
eval_limit=5
export SELF_ANALYSE=0
export IGNORE_COST=1
export CONTINUE_ON_STEP=3
max_iter=$((CONTINUE_ON_STEP + 15))
num_workers=1
dataset=princeton-nlp/SWE-bench
split=test
export SWE_BENCH=1
./evaluation/benchmarks/swe_bench/scripts/run_infer.sh $model_config $git_version $agent $eval_limit $max_iter $num_workers $dataset $split
# espeak 'e'
