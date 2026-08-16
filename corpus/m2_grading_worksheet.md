# M2 advisor grading worksheet — 50-piece calibration sample

Hugo, acting as grader (2026-05-27). This is the **Delcamp + advisor-graded
calibration sample** path from `docs/M2_ADVISOR_PACKET.md` Q2 — you grade
these 50 from scratch and they replace the `dummy-v0` placeholder labels,
then the model is retrained on real judgement.

## How to use this

1. Click a piece's **▶ play** link — opens it in the live player (notation +
   tab + playback + loop + tempo). Play it through, or read it on the guitar.
2. Assign a **1–10** grade (same scale the corpus uses — Delcamp-style, where
   1 = absolute beginner, 10 = concert/virtuoso). Trust your gut; this is a
   calibration sample, not an exam.
3. Write it in the **You** column (or just tell me "row N: grade" and I'll fill
   the CSV). The **Now** column is the current placeholder grade — react to it,
   don't anchor on it.
4. You can do this in chunks by era across several sittings; it's resumable.

When grades are in, I run `scripts/m2_train.py` + `scripts/m2_apply_to_manifest.py`
and the real model lands.

## Calibration anchors (from `corpus/dummy_v0_consensus_check.md`)

Rough community/syllabus consensus, to keep your scale steady:

| Piece | ~Grade |
|---|---:|
| Greensleeves (trad. arr.) | 3 |
| Lágrima / Adelita (Tárrega) | 4 |
| Carcassi Étude No. 1 | 4 |
| Bourrée, BWV 996 (Bach) | 5 |
| Villa-Lobos Prélude No. 1 (full) | 6 |
| Capricho Árabe (Tárrega, full) | 7 |
| Asturias / Leyenda (full) | 8 |

## Renaissance  (3)

| # | Title | Composer | Now | You | Play |
|--:|---|---|:--:|:--:|---|
| 1 | Romanza (Spanish Romance) | Anonymous | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fromanza.musicxml) |
| 2 | Andante | Anonymous | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aanonymous%2Fandante%2Fandante.musicxml) |
| 3 | Spanish Romance | Anonymous | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAnonymous%2Fspanish-romance%2Fspanish-romance%23movement01) |

## Baroque  (5)

| # | Title | Composer | Now | You | Play |
|--:|---|---|:--:|:--:|---|
| 4 | Prelude | J.S. Bach | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FBachJS%2FBWV999%2FBach_Prelude_BWV999%2FBach_Prelude_BWV999%23movement01) |
| 5 | Air on the G String | Johann Sebastian Bach | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aj-s-bach%2Fair-on-the-g-string%2Fair-on-the-g-string.musicxml) |
| 6 | Suite E-Dur - BWV 1006a | Johann Sebastian Bach | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FBachJS%2FBWV1006a%2Fbwv-1006a_1g%2Fbwv-1006a_1g%23movement01) |
| 7 | Suite E-Dur - BWV 1006a | Johann Sebastian Bach | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FBachJS%2FBWV1006a%2Fbwv-1006a_2g%2Fbwv-1006a_2g%23movement01) |
| 8 | Suite E-Dur - BWV 1006a | Johann Sebastian Bach | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FBachJS%2FBWV1006a%2Fbwv-1006a_3g%2Fbwv-1006a_3g%23movement01) |

## Classical  (18)

| # | Title | Composer | Now | You | Play |
|--:|---|---|:--:|:--:|---|
| 9 | 24 Studies for the Guitar | Mauro Giuliani | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FGiulianiM%2FO100%2FGiulianiOp100No8%2FGiulianiOp100No8%23movement01) |
| 10 | 24 Studies for the Guitar | Fernando Sor | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FSorF%2FO35%2Fsorf_op35_no5%2Fsorf_op35_no5%23movement01) |
| 11 | 25 Progressive Studies | Fernando Sor | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FSorF%2FO60%2Fsor_op60-06%2Fsor_op60-06%23movement01) |
| 12 | Six Petites Pièces | Dionisio Aguado | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No5%2FAguadoOp4No5%23movement03) |
| 13 | Study in A Minor | Dionisio Aguado | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2Faminor-study%2Faminor-study%23movement01) |
| 14 | Six Petites Pièces | Dionisio Aguado | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No3%2FAguadoOp4No3%23movement04) |
| 15 | Six Petites Pièces, No. 1 | Dionisio Aguado | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No1%2FAguadoOp4No1%23movement01) |
| 16 | Six Petites Pièces, No. 2 | Dionisio Aguado | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No2%2FAguadoOp4No2%23movement01) |
| 17 | Six Petites Pièces, No. 4 | Dionisio Aguado | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No4%2FAguadoOp4No4%23movement03) |
| 18 | Study 3 | Matteo Carcassi | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Amatteo-carcassi%2Fstudy-3%2Fstudy-3.musicxml) |
| 19 | Six Petites Pièces | Dionisio Aguado | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No3%2FAguadoOp4No3%23movement03) |
| 20 | Six Petites Pièces, No. 1 | Dionisio Aguado | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No1%2FAguadoOp4No1%23movement02) |
| 21 | Six Petites Pièces, No. 2 | Dionisio Aguado | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No2%2FAguadoOp4No2%23movement02) |
| 22 | Six Petites Pièces, No. 4 | Dionisio Aguado | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FAguadoD%2FO4%2FAguadoOp4No4%2FAguadoOp4No4%23movement04) |
| 23 | 24 Studies for the Guitar | Fernando Sor | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FSorF%2FO35%2Fsorf_op35_no16%2Fsorf_op35_no16%23movement01) |
| 24 | 24 Studies for the Guitar | Fernando Sor | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FSorF%2FO35%2Fsorf_op35_no21%2Fsorf_op35_no21%23movement01) |
| 25 | Andante Largo | Fernando Sor | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FSorF%2FO5%2Fsor-op5-5%2Fsor-op5-5%23movement01) |
| 26 | Six divertissements pour la guitare | Fernando Sor | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FSorF%2FO2%2Fsor_op2_3%2Fsor_op2_3%23movement02) |

## Romantic  (7)

| # | Title | Composer | Now | You | Play |
|--:|---|---|:--:|:--:|---|
| 27 | Adelita | Francisco Tárrega | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fadelita.musicxml) |
| 28 | Capricho Árabe (Theme) | Francisco Tárrega | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fcapricho-arabe.musicxml) |
| 29 | Estudio in A minor | Francisco Tárrega | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Festudio-am.musicxml) |
| 30 | Lágrima | Francisco Tárrega | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Flagrima.musicxml) |
| 31 | Recuerdos de la Alhambra (Theme) | Francisco Tárrega | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Frecuerdos-theme.musicxml) |
| 32 | Etude in A minor | Johann Kaspar Mertz | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FMertzJK%2Fmertz_etude%2Fmertz_etude%23movement01) |
| 33 | Capricho Árabe | Francisco Tárrega | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/mutopia%3Aftp%2FTarregaF%2Fcapricho-arabe%2Fcapricho-arabe%23movement02) |

## Modern  (1)

| # | Title | Composer | Now | You | Play |
|--:|---|---|:--:|:--:|---|
| 34 | Prelude No. 1 in E minor (Theme) | Heitor Villa-Lobos | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fprelude-emin-villalobos.musicxml) |

## Unknown  (16)

| # | Title | Composer | Now | You | Play |
|--:|---|---|:--:|:--:|---|
| 35 | Asturias (Leyenda) - Theme | Isaac Albéniz | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fasturias-theme.musicxml) |
| 36 | Farruca | Traditional Flamenco | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Ffarruca.musicxml) |
| 37 | Greensleeves | Traditional English | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fgreensleeves.musicxml) |
| 38 | Notes on the High E String | Exercise | 3 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Ffirst-string-notes.musicxml) |
| 39 | Am - Dm - E Progression | Exercise | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fam-dm-e-progression.musicxml) |
| 40 | Basic Open Chords | Exercise | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3ALYD01%2Fmusic-teacher%40main%3Apublic%2Fpieces%2Fbasic-open-chords.musicxml) |
| 41 | new disorder | riffman hansgtr@hotmail.com | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Aarhanv%2Fug-dataset%40main%3Adataset-converted-xml%2FOpen%20D%2FMetal%2FCriminal%20-%20New%20Disorder.musicxml) |
| 42 | subconscious lee | lee konitz | 5 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Amoisur%2Fcourstrompette%40master%3Apublic%2FWikifonia.rendered%2Flee%20konitz%20-%20subconscious%20lee.musicxml) |
| 43 | Bourreé | J. S. Bach | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aj-s-bach%2Fbourree%2Fbourree.musicxml) |
| 44 | Jesu,  Joy of Man's Desiring | J. S. Bach | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aj-s-bach%2Fjesu-joy-of-mans-desiring%2Fjesu-joy-of-mans-desiring.musicxml) |
| 45 | Minueto I | J. S. Bach | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aj-s-bach%2Fminueto-I%2Fminueto-I.musicxml) |
| 46 | Odeon | Ernesto Nazareth | 6 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aernesto-nazareth%2Fodeon%2Fodeon.musicxml) |
| 47 | Bachianinha Nº 1 | Paulinho Nogueira | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Apaulinho-nogueira%2Fbachianinha-1%2Fbachianinha-1.musicxml) |
| 48 | Choral Chambers (Silksong) | Christopher Larkin, Arranged by Beyond the Guitar | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3AThePython10110%2FMuseScore%40master%3AConverted%2FMusicXML%2FSilksong%2FChoral%20Chambers%20on%20guitar%20%28Silksong%29.musicxml) |
| 49 | Romance de Amor | Antonio Rovira | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Aantonio-rovira%2Fromance-de-amor%2Fromance-de-amor.musicxml) |
| 50 | Se Ela Perguntar | Dilermando Reis | 7 |  | [▶ play](https://hugofara.github.io/graded-guitar/#/piece/gh%3Arodrigoborgesdeoliveira%2Fsheet-music-and-chords%40main%3Adilermando-reis%2Fse-ela-perguntar%2Fse-ela-perguntar.musicxml) |

---
*50 pieces. Generated 2026-05-27 from `corpus/dummy_advisor_grades.csv`.*
