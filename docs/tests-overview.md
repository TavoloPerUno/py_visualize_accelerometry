# Physical Performance Tests

The app ships with labels for four physical performance tests used in aging and clinical research. The app itself is sensor-agnostic — these labels are defaults, not constraints. You can annotate any accelerometry recording.

## Chair Stand Test

The Chair Stand Test measures lower-extremity strength and postural control. The participant sits in a standard armless chair (~43 cm high) with arms folded across the chest and is timed while standing up and sitting down. There are two common variants: Five Times Sit-to-Stand (5 reps as fast as possible) and 30-Second Chair Stand (as many reps as possible in 30 seconds).

Rising from a seated position is a prerequisite for functional independence, so this test is a common indicator of fall risk and physical decline in older adults.

**In accelerometry data:** chair stands produce periodic spikes as the participant moves between sitting and standing. Each rep is a high-amplitude burst with brief low-amplitude pauses in between.

![Chair Stand signal pattern](images/signal_chair_stand.svg)

**Annotation segments.** Chair Stand is the main example of an activity with multiple segments. Each sit-to-stand-to-sit cycle is one segment. A Five Times Sit-to-Stand episode has five segments; a 30-Second Chair Stand has however many the participant completed. Mark the whole episode as one Chairstand annotation, then add a Segment flag for each rep.

### References

- Jones, C. J., Rikli, R. E., & Beam, W. C. (1999). A 30-s chair-stand test as a measure of lower body strength in community-residing older adults. *Research Quarterly for Exercise and Sport*, 70(2), 113–119. [doi:10.1080/02701367.1999.10608028](https://doi.org/10.1080/02701367.1999.10608028)
- Guralnik, J. M., Simonsick, E. M., Ferrucci, L., et al. (1994). A short physical performance battery assessing lower extremity function: Association with self-reported disability and prediction of mortality and nursing home admission. *Journal of Gerontology*, 49(2), M85–M94. [doi:10.1093/geronj/49.2.M85](https://doi.org/10.1093/geronj/49.2.M85)

## Timed Up and Go (TUG)

The TUG test measures functional mobility and fall risk. The participant rises from a seated position, walks 3 meters at a comfortable pace, turns, walks back, and sits. The full sequence is timed.

Per CDC STEADI guidelines, an older adult who takes 12 seconds or longer to complete the TUG is at increased risk of falling.

**In accelerometry data:** a sit-to-stand burst, a walking segment with rhythmic gait, a turn (brief deceleration then acceleration), another walking segment, and a stand-to-sit burst.

![TUG signal pattern](images/signal_tug.svg)

**Annotation segments.** TUG is one continuous movement, so it usually gets one segment covering the full episode. The segment can also carry the scoring flag.

### References

- Podsiadlo, D., & Richardson, S. (1991). The Timed "Up & Go": A test of basic functional mobility for frail elderly persons. *Journal of the American Geriatrics Society*, 39(2), 142–148. [doi:10.1111/j.1532-5415.1991.tb01616.x](https://doi.org/10.1111/j.1532-5415.1991.tb01616.x)
- Shumway-Cook, A., Brauer, S., & Woollacott, M. (2000). Predicting the probability for falls in community-dwelling older adults using the Timed Up & Go test. *Physical Therapy*, 80(9), 896–903. [doi:10.1093/ptj/80.9.896](https://doi.org/10.1093/ptj/80.9.896)
- CDC STEADI — Stopping Elderly Accidents, Deaths & Injuries. [https://www.cdc.gov/steadi/](https://www.cdc.gov/steadi/)

## 3-Meter Walk Test

The 3-Meter Walk Test measures gait speed as an indicator of mobility and physical function. The participant walks 3 meters at their usual pace, timed. Gait speed (meters/second) is derived from the result.

This test fits constrained spaces like in-home assessments. Gait speed has been called "the sixth vital sign" because it predicts mortality, disability, and hospitalization in older adults.

**In accelerometry data:** a short burst of rhythmic tri-axial oscillations matching the gait cycle.

![3-Meter Walk signal pattern](images/signal_3m_walk.svg)

**Annotation segments.** Usually one segment for the full walk. If the protocol has multiple trials, each trial is a separate segment within the episode, and the annotator picks the cleanest one for scoring.

### References

- Studenski, S., Perera, S., Patel, K., et al. (2011). Gait speed and survival in older adults. *JAMA*, 305(1), 50–58. [doi:10.1001/jama.2010.1923](https://doi.org/10.1001/jama.2010.1923)
- Fritz, S., & Lusardi, M. (2009). White paper: "Walking speed: The sixth vital sign." *Journal of Geriatric Physical Therapy*, 32(2), 46–49. [doi:10.1519/00139143-200932020-00002](https://doi.org/10.1519/00139143-200932020-00002)
- Peel, N. M., Kuys, S. S., & Klein, K. (2013). Gait speed as a measure in geriatric assessment in clinical settings: A systematic review. *The Journals of Gerontology: Series A*, 68(1), 39–46. [doi:10.1093/gerona/gls174](https://doi.org/10.1093/gerona/gls174)

## 6-Minute Walk Test (6MWT)

The 6MWT is a submaximal exercise test that measures aerobic capacity and endurance. The participant walks as far as possible along a flat corridor for 6 minutes at a self-selected pace. The outcome is the total distance.

Clinical and research settings use it to evaluate patients with cardiac and pulmonary conditions (heart failure, COPD). No special equipment is required.

**In accelerometry data:** a sustained run of rhythmic gait oscillations, sometimes with gradual amplitude or frequency changes as fatigue sets in. Brief disruptions are corridor turns.

![6-Minute Walk signal pattern](images/signal_6min_walk.svg)

**Annotation segments.** Usually one segment for the entire walk. If the participant rests or the protocol uses corridor turn-arounds, you can mark start/stop or turn segments, but it isn't required. One segment with the scoring flag is enough for most use cases.

### References

- ATS Committee on Proficiency Standards for Clinical Pulmonary Function Laboratories. (2002). ATS statement: Guidelines for the six-minute walk test. *American Journal of Respiratory and Critical Care Medicine*, 166(1), 111–117. [doi:10.1164/ajrccm.166.1.at1102](https://doi.org/10.1164/ajrccm.166.1.at1102)
- Enright, P. L. (2003). The six-minute walk test. *Respiratory Care*, 48(8), 783–785. [PMID: 12890299](https://pubmed.ncbi.nlm.nih.gov/12890299/)
- Bohannon, R. W., & Crouch, R. (2017). Minimal clinically important difference for change in 6-minute walk test distance of adults with pathology: A systematic review. *Journal of Evaluation in Clinical Practice*, 23(2), 377–381. [doi:10.1111/jep.12629](https://doi.org/10.1111/jep.12629)

## Context: NSHAP Study

These tests are part of the **National Social Life, Health, and Aging Project (NSHAP)**, a longitudinal study of health and social factors in older Americans run at the University of Chicago. Accelerometry data is collected during in-home assessments to measure physical activity and functional performance objectively.

### References

- Suzman, R. (2009). The National Social Life, Health, and Aging Project: An Introduction. *The Journals of Gerontology Series B: Psychological Sciences and Social Sciences*, 64B(Suppl 1), i5–i11. [doi:10.1093/geronb/gbp078](https://doi.org/10.1093/geronb/gbp078)
- Huisingh-Scheetz, M., Kocherginsky, M., Magett, E., Rush, P., Dale, W., & Waite, L. (2016). Relating wrist accelerometry measures to disability in older adults. *Archives of Gerontology and Geriatrics*, 62, 68–74. [doi:10.1016/j.archger.2015.09.004](https://doi.org/10.1016/j.archger.2015.09.004)
