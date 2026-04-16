# SROI Report Generation System
**Production Bundle — Baseline Sprint 14E**

Pipeline deterministik untuk produksi laporan SROI TJSL:
intake → canonical → financial → narrative → QA → render → style refinement → batch orchestration

---

## Prasyarat

| Tool | Versi minimum | Cek |
|------|--------------|-----|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 8+ | `npm --version` |

---

## Instalasi (sekali saja)

```bash
# Clone atau extract bundle ini ke folder lokal
cd sroi-report-system

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

---

## Jalur A — Local Machine

### Produksi laporan (canonical sudah ada)

```bash
python run.py --program ESL
```

### Produksi laporan dengan input baru

```bash
python run.py --program ESL --scripts /path/to/TJSL_Scripts.md
```

### Hanya batch refinement (skip core pipeline)

```bash
python run.py --program ESL --only-refine
```

### Dry run — lihat rencana tanpa eksekusi

```bash
python run.py --program ESL --dry-run
```

### Output

Laporan Word tersimpan di:
- `sprint14e/ESL_SROI_Full_Report_Refined.docx` — full report setelah batch refinement
- `output/esl/ESL_SROI_Report_Full.docx` — output core pipeline

---

## Jalur B — GitHub Actions

### Setup

1. Push seluruh folder ini ke GitHub repo (private)
2. Pastikan Actions diaktifkan di repo settings
3. Tidak perlu konfigurasi secrets — pipeline tidak menggunakan API key

### Trigger manual

1. Buka tab **Actions** di repo
2. Pilih workflow **Generate SROI Report**
3. Klik **Run workflow**
4. Pilih program (ESL / PSN / dll.) dan mode
5. Tunggu ~5–10 menit
6. Download hasil dari tab **Artifacts**

### Trigger otomatis

Pipeline berjalan otomatis setiap kali ada file baru di `data/canonical/`.

Untuk menambahkan program baru: upload `canonical_{PROGRAM}_v1.json` ke `data/canonical/`.

---

## Struktur direktori

```
sroi-report-system/
├── run.py                          ← Entry point utama
├── requirements.txt                ← Python deps
├── package.json                    ← Node.js deps
├── .github/
│   └── workflows/
│       └── generate-report.yml     ← GitHub Actions
├── data/
│   ├── canonical/
│   │   └── canonical_esl_v1.json   ← Input utama per program
│   └── semantic/
│       └── chapter_semantic_bab*.json
├── sprint0/    ← Canonical schema + render contract
├── sprint1/    ← Financial engine
├── sprint2/    ← Report architect
├── sprint3/    ← Point builder + narrative builder (SROI)
├── sprint4/    ← Renderer (Node.js → .docx)
├── sprint5/    ← QA checker
├── sprint6/    ← Narrative builder (rest babs)
├── sprint7/    ← Source extractor
├── sprint8/    ← Full assembler (Node.js → full report)
├── sprint9/    ← Orchestrator (koordinator pipeline inti)
├── sprint10/   ← Input parsers (doc, free text, ESS)
├── sprint11/   ← Human review loop
├── sprint12/   ← Enrichment engine (ontology/NLP)
├── sprint13/   ← Chat review bridge
├── sprint14a/  ← Style profile (rule-based personalization)
├── sprint14b/  ← Exemplar-driven style learning
├── sprint14c/  ← Per-register calibration
├── sprint14d/  ← Paragraph-level style application
├── sprint14e/  ← Batch refinement orchestration
└── output/     ← Hasil pipeline (git-ignored)
```

---

## Menambahkan program baru (PSN, ESD, dll.)

1. Buat canonical JSON: `data/canonical/canonical_psn_v1.json`
   (ikuti schema dari `sprint0/canonical_esl_v1.json`)

2. Tambahkan chapter semantics ke `data/semantic/`
   (ikuti schema dari file `chapter_semantic_bab_*.json` yang ada)

3. Update `sprint14e/batch_refinement_config.json`:
   ```json
   { "program": "PSN", "applicability_context": "PSN_Pertamina_2025", ... }
   ```

4. Jalankan:
   ```bash
   python run.py --program PSN
   ```

---

## Troubleshooting

| Error | Solusi |
|-------|--------|
| `canonical_*.json not found` | Pastikan file ada di `data/canonical/` |
| `node: command not found` | Install Node.js 18+ |
| `ModuleNotFoundError: docx` | Jalankan `pip install -r requirements.txt` |
| `renderer.js` gagal | Jalankan `npm install` di root folder |

---

## Status pipeline

Core production engine di-freeze di Sprint 14E.
Untuk penambahan kapabilitas editorial (EIS layer), lihat roadmap terpisah.
