"""Reproduce a fixed outcome-blind passage sample and full-score descriptive EDA."""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rhetoric_scoring import read_cache, validate_scores, SPEC_HASH
from analysis_eda import run_eda


def main():
    output = ROOT / 'outputs/whole_speech_eda'
    output.mkdir(parents=True, exist_ok=True)
    prepared = pd.read_parquet(ROOT / 'outputs/prepared.parquet')
    scores = read_cache(ROOT / 'outputs/rhetoric_full.sqlite')
    validated = validate_scores(prepared, scores)
    regions = pd.read_csv(ROOT / 'config/region_income_snapshot.csv')
    regions['region'] = regions.region.str.strip()
    # The sample-building frame deliberately excludes conflict and spending fields.
    texts = prepared[['entity_id','country_name','year','speech_clean','main_population']].merge(
        regions[['entity_id','region']], on='entity_id', validate='many_to_one').merge(
        scores[['entity_id','year','chunks']], on=['entity_id','year'], validate='one_to_one')
    texts = texts[texts.main_population & texts.year.between(1990,2024)]
    passages = []
    for row in texts.itertuples():
        era = '1990–2001' if row.year <= 2001 else ('2002–2013' if row.year <= 2013 else '2014–2024')
        for i,c in enumerate(row.chunks):
            passages.append({'entity_id':row.entity_id,'country_name':row.country_name,'year':row.year,
                'region':row.region,'era':era,'chunk_index':i,'trust':c['trust'],'threat':c['threat'],
                'text':row.speech_clean[c['start_char']:c['end_char']],
                'start_token':c['start_token'],'end_token':c['end_token']})
    passages = pd.DataFrame(passages).sort_values(['year','entity_id','chunk_index'])
    selected, used, region_counts = [], set(), {}
    for theme in ['trust','threat']:
        for era in ['1990–2001','2002–2013','2014–2024']:
            subset = passages[passages.era.eq(era)]
            ranks = subset[theme].rank(method='average', pct=True)
            for band,lo,hi in [('low',0,.1),('middle',.45,.55),('high',.9,1)]:
                pool = subset[ranks.between(lo,hi)].copy()
                pool = pool[~pool.apply(lambda r:(r.entity_id,r.year) in used,axis=1)]
                pool['region_used'] = pool.region.map(region_counts).fillna(0)
                pool = pool[pool.region_used.eq(pool.region_used.min())]
                r = pool.sample(1,random_state=20260926).iloc[0].to_dict()
                r.update(review_id=f'P{len(selected)+1:02}', selection_theme=theme, selection_band=band)
                used.add((r['entity_id'],r['year']))
                region_counts[r['region']] = region_counts.get(r['region'],0)+1
                selected.append(r)
    review = pd.DataFrame(selected).drop(columns='region_used')
    review.to_csv(output / 'passage_review_key.csv',index=False)
    blind = review[['review_id','country_name','year','region','text']].copy()
    for column in ['human_trust_theme_0_1_2','human_threat_theme_0_1_2','own_foreign_or_unspecified',
                   'ceremonial_or_substantive','ambiguity_notes']:
        blind[column] = ''
    review_path = output / 'passage_review_blinded.csv'
    if review_path.exists():
        # A teammate may have filled in ratings. Never erase them on an EDA rerun.
        existing = pd.read_csv(review_path, keep_default_na=False)
        identity_columns = ['review_id','country_name','year','region','text']
        pd.testing.assert_frame_equal(existing[identity_columns], blind[identity_columns],
                                      check_dtype=False)
    else:
        blind.to_csv(review_path,index=False)
    lines = ['# Passage review: outcomes and model scores omitted\n']
    for r in blind.itertuples():
        lines.extend([f'## {r.review_id}: {r.country_name}, {r.year} ({r.region})\n',r.text+'\n'])
    (output / 'passages_blinded.md').write_text('\n'.join(lines))
    sample_manifest = {'seed':20260926,'sampling':'2 themes × 3 eras × 3 score bands; random within least represented region; no repeated speech',
        'bands':'within-era passage-score percentile 0–10, 45–55, 90–100',
        'outcomes_used':False,'regions':region_counts,'n':len(review),'spec_hash':SPEC_HASH,
        'sample_sha256':hashlib.sha256(review.to_csv(index=False).encode()).hexdigest(),
        'limitations':'Purposive stratification; not a population accuracy estimate. Reviewer sees country/year but not scores/outcomes.'}
    (output / 'review_sampling_manifest.json').write_text(json.dumps(sample_manifest,indent=2))
    print('Sample written:',len(review),'passages;',region_counts,flush=True)
    analysis = prepared.merge(validated.drop(columns='chunks'),on=['entity_id','year'],validate='one_to_one').merge(
        regions,on='entity_id',how='left',validate='many_to_one')
    print(json.dumps(run_eda(analysis,output),indent=2),flush=True)


if __name__ == '__main__':
    main()
