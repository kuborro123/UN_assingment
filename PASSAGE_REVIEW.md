# Full-speech passage review — 26 September 2026

This is an **AI-assisted qualitative inspection**, not independent human ground
truth, a model accuracy estimate or validation of countries' actual trust/intent.
The first-pass judgements below were recorded after reading passages with numeric
scores and conflict outcomes withheld. The reviewer knew the sampling design.
Country and year were visible. No model labels, prompts or scores were changed.

## Reproducible sample and review rule

`scripts/review_and_eda.py` selects 18 passages using seed 20260926: two theme
scores × three eras (1990–2001, 2002–2013, 2014–2024) × low/middle/high within-era
passage-score bands (bottom 10%, 45th–55th percentiles, top 10%). Within each
stratum it randomly selects from the least-represented available region and
avoids repeated speeches. All seven current World Bank regions appear. Conflict
and spending fields are not supplied to the sampler. This intentionally diverse
sample is not representative of all passages and oversamples score extremes.

First-pass rubric for each theme: 0 = absent; 1 = passing/background mention;
2 = substantive discussion. Ratings concern discussion, not approval. Trust/
cooperation includes international coordination and negotiated solutions;
military-threat discussion includes weapons, armed violence and disarmament.
This interpretive rubric is broader than the model's particular label wording.

| ID | Country/year | Cooperation discussion | Military-threat discussion | Meaning and qualification |
| --- | --- | ---: | ---: | --- |
| P01 | Eritrea 2001 | 2 | 2 | African conflicts, regional mediation and international assistance; both domestic/bilateral and foreign situations, plus poverty and disease. |
| P02 | Germany 2001 | 2 | 2 | Weapons control, terrorism and multilateral governance; also development/environment. Stray page number 14 remains. |
| P03 | Ecuador 2000 | 2 | 0 | Multilateral rules and development cooperation; praise of the UN accompanies substantive argument. Stray page number 18 remains. |
| P04 | Nepal 2006 | 2 | 0 | International development commitments and Bhutanese refugees; humanitarian insecurity is not explicit military threat. Page/header residue remains. |
| P05 | Iran 2013 | 2 | 2 | Offers international cooperation and rejects militarism while discussing regional crises/nuclear negotiations. Antiwar statements must not become an aggression label. |
| P06 | Samoa 2013 | 2 | 0 | Concrete international partnerships for small-island development, with closing thanks. |
| P07 | United States 2015 | 1 | 2 | Military action against ISIL and Syria, with a clear but secondary offer to cooperate with Russia/Iran. Own involvement and foreign conflict coexist. |
| P08 | Romania 2016 | 2 | 2 | Humanitarian coordination and multilateral responses to terrorism; largely foreign/global rather than domestic conflict. |
| P09 | Malta 2021 | 2 | 0 | COVID cooperation and multilateral recovery, not armed conflict; ceremonial salutation and joined OCR word remain. |
| P10 | Brazil 1990 | 2 | 0 | International trade cooperation and protectionism; military metaphors such as arsenal/fortresses are economic, not literal. OCR errors remain. |
| P11 | Vietnam 1993 | 2 | 1 | Sovereignty, negotiations and UN security governance; abstract dispute prevention rather than a concrete military threat. |
| P12 | Malawi 1999 | 2 | 2 | Condemns arms flows and foreign wars; supports peaceful settlements. Strong weapons discussion does not imply militaristic intent. |
| P13 | Bangladesh 2009 | 2 | 0 | Domestic social policy and international agriculture agreements; food security is not military security. |
| P14 | United States 2010 | 2 | 1 | Introductory shared challenges and economic coordination, with historical terrorist attacks; mixed ceremonial/substantive framing. |
| P15 | Kazakhstan 2013 | 2 | 2 | Nuclear abolition, treaties and dialogue; sustained weapons discussion is explicitly pro-disarmament. |
| P16 | Kuwait 2022 | 1 | 0 | Short closing passage congratulating Qatar on the World Cup; goodwill, not substantive security policy. |
| P17 | Indonesia 2020 | 2 | 1 | Multilateralism, ASEAN and peaceful dispute resolution; foreign Palestine reference. Frequent transcription ellipses remain. |
| P18 | Chad 2019 | 2 | 2 | Own/regional counterterrorism, joint forces and Libya; cooperation and military-threat themes are simultaneously substantive. |

## Interpretation after revealing the model scores

Several extreme scores have a clear thematic reading: Ecuador 2000, Samoa 2013
and Malta 2021 have high cooperation scores (0.970, 0.931, 0.963); Brazil's trade
metaphors and Bangladesh's food security receive very low military-threat scores.
Malawi 1999, Kazakhstan 2013 and Chad 2019 have high threat scores (0.897, 0.972,
0.843). But Kazakhstan is advocating nuclear abolition, and Malawi condemns arms
flows. High scores therefore cannot mean aggression or willingness to wage war.

There are also substantial disagreements with a broad discussion-of-theme rubric:
Eritrea 2001 explicitly discusses conflicts and mediation but receives trust
0.005 and threat 0.001. Nepal's international development appeals score only 0.009
on cooperation. Chad's substantive joint-force cooperation scores only 0.024 on
cooperation. Mixed-topic passages and the exact label wording can make real
mentions receive low compatibility. A low score does not establish absence of a
theme, and the two independent scores can under-recognize co-occurring themes.

Conclusion: the sample supports describing these as **model-derived compatibility
scores**, with useful examples but clear measurement limitations. It does not
establish a validated trust or threat scale. Keep the frozen labels and record
these weaknesses; do not retune against conflict differences. Human annotation
and any future prompt sensitivity must remain separate from outcome-based choice.

## Human follow-up instructions

The generated `outputs/whole_speech_eda/passage_review_blinded.csv` contains the
same excerpts and empty rating fields, but no model scores/outcomes. Ask one or
preferably two teammates to read and rate it independently using the rubric,
before opening `passage_review_key.csv` or this judgement table. Disagreements
are useful evidence of ambiguous constructs, not a reason to tune labels against
conflict outcomes. A person who has already read these AI ratings is not an
independent blinded annotator; disclose that if applicable.

Primary text comparisons exclude 2025. This sample therefore does not validate
the separate 2025 chair-introduction removal procedure. Small OCR/transcription
artefacts remain in earlier years as well. We do not infer an error rate or
claim these 18 passages rule out country-name, translation or length effects.
