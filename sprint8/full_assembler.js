/**
 * Full Assembler — Sprint 8
 * SROI Report System
 *
 * Input : chapter_semantic_bab_[1-9].json (semua bab)
 *         canonical_esl_v1.json (untuk cover + metadata)
 * Output: ESL_SROI_Report_Full.docx (laporan utuh 9 bab)
 *
 * Fitur:
 *   - Halaman sampul (cover)
 *   - Halaman verifikasi
 *   - Daftar Isi (TOC manual)
 *   - Bab 1–9 assembled
 *   - Header + footer konsisten
 *   - Page break antar bab
 *
 * Usage:
 *   node full_assembler.js
 *   node full_assembler.js --semantic-dir /p/ --canonical /p/ --output /p/
 *   SEMANTIC_DIR=... CANONICAL_FILE=... OUTPUT_FILE=... node full_assembler.js
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, LevelFormat, TabStopType, PageBreak,
  NumberFormat
} = require('docx');
const fs   = require('fs');
const path = require('path');

// ── PATH CONFIG ───────────────────────────────────────────────
const args = process.argv.slice(2);
const argMap = {};
for (let i = 0; i < args.length; i += 2) {
  if (args[i] && args[i].startsWith('--')) argMap[args[i].slice(2)] = args[i+1];
}

const SCRIPT_DIR   = __dirname;
const SEMANTIC_DIR  = argMap['semantic-dir']
  || process.env.SEMANTIC_DIR
  || path.join(SCRIPT_DIR, '../sprint3');          // bab_7 ada di sprint3
const SEMANTIC_DIR6 = argMap['semantic-dir6']
  || process.env.SEMANTIC_DIR6
  || path.join(SCRIPT_DIR, '../sprint6');          // bab 1-6,8-9 ada di sprint6
const CANONICAL_FILE= argMap['canonical']
  || process.env.CANONICAL_FILE
  || path.join(SCRIPT_DIR, '../sprint0/canonical_esl_v1.json');
const OUTPUT_FILE   = argMap['output']
  || process.env.OUTPUT_FILE
  || path.join(SCRIPT_DIR, 'ESL_SROI_Report_Full.docx');

console.log(`Semantic dir (bab7) : ${path.resolve(SEMANTIC_DIR)}`);
console.log(`Semantic dir (rest) : ${path.resolve(SEMANTIC_DIR6)}`);
console.log(`Canonical           : ${path.resolve(CANONICAL_FILE)}`);
console.log(`Output              : ${path.resolve(OUTPUT_FILE)}`);

// ── LOAD DATA ─────────────────────────────────────────────────
const canonical = JSON.parse(fs.readFileSync(CANONICAL_FILE, 'utf8'));
const pi  = canonical.program_identity;
const pp  = canonical.program_positioning;
const sm  = canonical.sroi_metrics.calculated;

// Load semua bab dalam urutan
const BAB_ORDER = [1,2,3,4,5,6,7,8,9];
const chaptersMap = {};

// Bab 7 dari sprint3
const bab7raw = JSON.parse(fs.readFileSync(
  path.join(SEMANTIC_DIR, 'chapter_semantic_bab7.json'), 'utf8'
));
chaptersMap[7] = (Array.isArray(bab7raw) ? bab7raw[0] : bab7raw);

// Bab 1-6, 8-9 dari sprint6
for (const n of [1,2,3,4,5,6,8,9]) {
  const f = path.join(SEMANTIC_DIR6, `chapter_semantic_bab_${n}.json`);
  if (fs.existsSync(f)) {
    const raw = JSON.parse(fs.readFileSync(f, 'utf8'));
    chaptersMap[n] = (Array.isArray(raw) ? raw[0] : raw);
  }
}

const totalBlocks = Object.values(chaptersMap).reduce((s,c) => s + c.blocks.length, 0);
console.log(`\nLoaded ${Object.keys(chaptersMap).length} bab, ${totalBlocks} blocks total`);

// ── COLOUR PALETTE (Marine Teal — ESL) ───────────────────────
const C = {
  navy:    '0D2B2B', navyMid: '1A4040', teal:   '0A6B6B',
  tealLt:  '00B4B4', orange: 'E8541A', amber:  'E67E22',
  green:   '1A7A50', white:  'FFFFFF', gray:   '555555',
  grayLt:  'CCCCCC', bgTeal: 'EAF5F5', bgBlue: 'EEF4FA',
  bgWarm:  'FDF5E8', bgGreen:'EAF5EE', bgGray: 'F4F4F4',
};

// ── CONSTANTS ─────────────────────────────────────────────────
const MARGIN  = 1134;
const CW      = 11906 - 2 * MARGIN;   // 9638 DXA
const idr     = v => `Rp ${Number(v).toLocaleString('id-ID')}`;
const ratio   = v => `1 : ${Number(v).toFixed(2)}`;

// ── BORDER / SHADING HELPERS ──────────────────────────────────
const bdr   = (col=C.grayLt, sz=4) => ({ style: BorderStyle.SINGLE, size: sz, color: col });
const bAll  = (col=C.grayLt)       => ({ top:bdr(col),bottom:bdr(col),left:bdr(col),right:bdr(col) });
const bNone = ()                    => ({ style: BorderStyle.NONE, size: 0, color: 'FFFFFF' });
const bAllN = ()                    => ({ top:bNone(),bottom:bNone(),left:bNone(),right:bNone() });

// ── TEXT HELPERS ──────────────────────────────────────────────
const run  = (text, opts={}) => new TextRun({ text, font:'Arial', size:22, ...opts });
const runS = (text, opts={}) => new TextRun({ text, font:'Arial', size:18, ...opts });

// ── PARAGRAPH HELPERS ─────────────────────────────────────────
const sp = (bf=0, af=120, ln=320) => ({ before:bf, after:af, line:ln });
const gap = (pts=100) => new Paragraph({ children:[run('')], spacing:{before:0,after:pts} });

// ══════════════════════════════════════════════════════════════
// COVER PAGE
// ══════════════════════════════════════════════════════════════
function buildCoverPage() {
  const children = [];

  // Accent bar (simulated with bordered paragraph)
  children.push(new Paragraph({
    children: [run('')],
    spacing:  { before: 0, after: 0 },
    border:   { top: { style: BorderStyle.SINGLE, size: 24, color: C.teal, space: 0 } },
  }));

  children.push(gap(400));

  // Company tag
  children.push(new Paragraph({
    children: [run(pi.company.toUpperCase(), { bold:true, color:C.teal, size:18, characterSpacing:60 })],
    alignment: AlignmentType.LEFT,
    spacing:   { before: 0, after: 60 },
  }));
  children.push(new Paragraph({
    children: [run('PROGRAM TJSL CSV', { color:C.gray, size:16, characterSpacing:40 })],
    alignment: AlignmentType.LEFT,
    spacing:   { before: 0, after: 240 },
  }));

  // Main title
  children.push(new Paragraph({
    children: [new TextRun({ text: pi.program_name.toUpperCase(), font:'Arial Black', size:64, bold:true, color:C.navy })],
    alignment: AlignmentType.LEFT,
    spacing:   { before: 0, after: 120 },
  }));

  // Tagline
  children.push(new Paragraph({
    children: [run(pi.program_tagline, { size:24, color:C.gray })],
    alignment: AlignmentType.LEFT,
    spacing:   { before: 0, after: 480 },
  }));

  // Divider
  children.push(new Paragraph({
    children: [run('')],
    border:   { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.teal, space: 4 } },
    spacing:  { before: 0, after: 160 },
  }));

  // Key stats (3 boxes via table)
  const statItems = [
    { label:'Periode Program', value:`${pi.period_start}–${pi.period_end}` },
    { label:'SROI Blended',    value:ratio(sm.sroi_blended) },
    { label:'Total Investasi', value:idr(sm.total_investment_idr) },
  ];
  const statW = Math.floor(CW / 3);
  children.push(new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [statW, statW, CW - 2*statW],
    rows: [new TableRow({ children: statItems.map((s,i) =>
      new TableCell({
        children: [
          new Paragraph({ children:[runS(s.label, { color:C.teal })], spacing:{before:0,after:40} }),
          new Paragraph({ children:[new TextRun({ text:s.value, font:'Arial', size:32, bold:true, color:C.navy })], spacing:{before:0,after:0} }),
        ],
        width:   { size: i<2 ? statW : CW-2*statW, type: WidthType.DXA },
        borders: bAllN(),
        shading: { fill: i%2===0 ? C.bgTeal : C.bgBlue, type: ShadingType.CLEAR },
        margins: { top:160, bottom:160, left:180, right:180 },
      })
    )})]
  }));

  children.push(gap(240));

  // SDG alignment
  children.push(new Paragraph({
    children: [run('Keselarasan SDGs: ' + pp.sdg_alignment.join('  ·  '), { size:18, color:C.gray })],
    spacing:  { before: 0, after: 80 },
  }));
  children.push(new Paragraph({
    children: [run(`Kategori PROPER: ${pp.proper_category}`, { size:18, color:C.gray })],
    spacing:  { before: 0, after: 0 },
  }));

  children.push(gap(480));

  // Footer cover
  children.push(new Paragraph({
    children: [run('Laporan Evaluasi Social Return on Investment (SROI)', { color:C.navy, bold:true })],
    spacing:  { before: 0, after: 40 },
    border:   { top: { style: BorderStyle.SINGLE, size: 4, color: C.tealLt, space: 4 } },
  }));
  children.push(new Paragraph({
    children: [run(`Disusun oleh PT Dipa Konsultan Utama  ·  ${pi.period_end}`, { color:C.gray, size:18 })],
    spacing:  { before: 0, after: 0 },
  }));

  children.push(new Paragraph({ children:[new PageBreak()] }));
  return children;
}

// ══════════════════════════════════════════════════════════════
// HALAMAN VERIFIKASI
// ══════════════════════════════════════════════════════════════
function buildVerificationPage() {
  const children = [];

  children.push(new Paragraph({
    heading:   HeadingLevel.HEADING_1,
    children:  [new TextRun({ text:'LEMBAR VERIFIKASI', font:'Arial', size:36, bold:true, color:C.navy })],
    spacing:   sp(0, 240),
    border:    { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.teal, space: 4 } },
  }));

  const rows = [
    ['Judul',         `Laporan Kajian Social Return on Investment (SROI) Program ${pi.program_name}`],
    ['Nama Perusahaan', pi.company],
    ['Jenis Industri',  'Energi — Pelumas dan Distribusi'],
    ['Periode Evaluasi', `${pi.period_start}–${pi.period_end}`],
    ['Penyusun',        'PT Dipa Konsultan Utama'],
    ['Status Data',     'Evaluatif · Compound ORI-adjusted · DDAT per aspek'],
  ];

  children.push(new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [2800, 6838],
    rows: rows.map(([label, value]) => new TableRow({
      children: [
        new TableCell({
          children: [new Paragraph({ children:[run(label, { bold:true, color:C.navy })], spacing:{before:0,after:0} })],
          width: { size:2800, type:WidthType.DXA },
          borders: bAll(C.grayLt),
          shading: { fill:C.bgTeal, type:ShadingType.CLEAR },
          margins: { top:80, bottom:80, left:120, right:120 },
        }),
        new TableCell({
          children: [new Paragraph({ children:[run(value)], spacing:{before:0,after:0} })],
          width: { size:6838, type:WidthType.DXA },
          borders: bAll(C.grayLt),
          margins: { top:80, bottom:80, left:120, right:120 },
        }),
      ],
    })),
  }));

  children.push(gap(320));
  children.push(new Paragraph({
    children: [run('Semarang, ' + pi.period_end, { color:C.gray })],
    spacing:  sp(0,80),
  }));
  children.push(new Paragraph({
    children: [run('PT Dipa Konsultan Utama', { bold:true })],
    spacing:  sp(0,320),
  }));
  children.push(new Paragraph({ children:[new PageBreak()] }));
  return children;
}

// ══════════════════════════════════════════════════════════════
// TABLE OF CONTENTS (manual)
// ══════════════════════════════════════════════════════════════
const TOC_ENTRIES = [
  { label:'LEMBAR VERIFIKASI',                  page:'ii',  level:0 },
  { label:'KATA PENGANTAR',                     page:'iii', level:0 },
  { label:'RINGKASAN EKSEKUTIF',                page:'iv',  level:0 },
  { label:'BAB I PENDAHULUAN',                  page:'1',   level:0 },
  { label:'1.1 Latar Belakang Penulisan Laporan SROI', page:'2', level:1 },
  { label:'1.2 Tujuan dan Luaran',              page:'3',   level:1 },
  { label:'1.3 Ruang Lingkup Kajian',           page:'4',   level:1 },
  { label:'1.4 Konsiderasi Hukum',              page:'4',   level:1 },
  { label:'BAB II PROFIL PERUSAHAAN',           page:'5',   level:0 },
  { label:'BAB III METODOLOGI SROI',            page:'8',   level:0 },
  { label:'BAB IV IDENTIFIKASI KONDISI AWAL',   page:'14',  level:0 },
  { label:'BAB V IDENTIFIKASI KONDISI IDEAL',   page:'18',  level:0 },
  { label:'BAB VI STRATEGI PROGRAM',            page:'22',  level:0 },
  { label:'BAB VII IMPLEMENTASI / PDIS DENGAN SROI', page:'28', level:0 },
  { label:'7.1 Proses dan Kegiatan',            page:'29',  level:1 },
  { label:'7.4 Input / Investasi',              page:'31',  level:1 },
  { label:'7.7 Fiksasi Dampak (DDAT)',          page:'33',  level:1 },
  { label:'7.8 Monetisasi Dampak',              page:'34',  level:1 },
  { label:'7.9 Nilai SROI dan Penjelasan',      page:'36',  level:1 },
  { label:'BAB VIII ASPEK PEMBELAJARAN',        page:'40',  level:0 },
  { label:'BAB IX PENUTUP',                     page:'45',  level:0 },
];

function buildTOC() {
  const children = [];

  children.push(new Paragraph({
    heading:  HeadingLevel.HEADING_1,
    children: [new TextRun({ text:'DAFTAR ISI', font:'Arial', size:36, bold:true, color:C.navy })],
    spacing:  sp(0, 240),
    border:   { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.teal, space: 4 } },
  }));

  for (const entry of TOC_ENTRIES) {
    const indent = entry.level === 1 ? 560 : 0;
    const bold   = entry.level === 0;
    const col    = entry.level === 0 ? C.navy : '222222';

    children.push(new Paragraph({
      children: [
        new TextRun({ text: entry.label, font:'Arial', size: bold ? 22 : 20, bold, color: col }),
        new TextRun({ text: '\t', font:'Arial', size:20 }),
        new TextRun({ text: entry.page, font:'Arial', size:20, color: C.teal }),
      ],
      indent:   { left: indent },
      tabStops: [{ type: TabStopType.RIGHT, position: CW, leader: 'dot' }],
      spacing:  { before: bold ? 80 : 0, after: bold ? 60 : 40 },
    }));
  }

  children.push(new Paragraph({ children:[new PageBreak()] }));
  return children;
}

// ══════════════════════════════════════════════════════════════
// KATA PENGANTAR + RINGKASAN EKSEKUTIF (generated)
// ══════════════════════════════════════════════════════════════
function buildKataPengantar() {
  const children = [];
  children.push(new Paragraph({
    heading:  HeadingLevel.HEADING_1,
    children: [new TextRun({ text:'KATA PENGANTAR', font:'Arial', size:36, bold:true, color:C.navy })],
    spacing:  sp(0, 200),
    border:   { bottom: { style:BorderStyle.SINGLE, size:8, color:C.teal, space:4 } },
  }));
  children.push(new Paragraph({
    children: [run(
      `Puji syukur kami panjatkan atas tersusunnya Laporan Kajian Social Return on Investment (SROI) ` +
      `Program ${pi.program_name} Tahun ${pi.period_start}–${pi.period_end}. Dokumen ini merupakan ` +
      `bagian dari komitmen ${pi.company} dalam memastikan pelaksanaan Tanggung Jawab Sosial dan ` +
      `Lingkungan (TJSL) berjalan sesuai prinsip keberlanjutan dan memenuhi ketentuan ${pp.proper_category}.`
    )],
    alignment: AlignmentType.JUSTIFIED, spacing: sp(0,160,340),
  }));
  children.push(new Paragraph({
    children: [run(
      `Kajian SROI ini menjadi instrumen evaluasi strategis untuk menilai nilai sosial yang dihasilkan ` +
      `oleh investasi sosial perusahaan, baik secara kuantitatif maupun kualitatif, pada level individu, ` +
      `komunitas, dan sistem kelembagaan.`
    )],
    alignment: AlignmentType.JUSTIFIED, spacing: sp(0,320,340),
  }));
  children.push(new Paragraph({
    children: [run(`${pi.company}`, { bold:true })],
    spacing:  sp(0,60),
  }));
  children.push(new Paragraph({
    children: [run(`Tahun ${pi.period_end}`, { color:C.gray })],
    spacing:  sp(0,0),
  }));
  children.push(new Paragraph({ children:[new PageBreak()] }));
  return children;
}

function buildRingkasanEksekutif() {
  const children = [];
  children.push(new Paragraph({
    heading:  HeadingLevel.HEADING_1,
    children: [new TextRun({ text:'RINGKASAN EKSEKUTIF', font:'Arial', size:36, bold:true, color:C.navy })],
    spacing:  sp(0, 200),
    border:   { bottom: { style:BorderStyle.SINGLE, size:8, color:C.teal, space:4 } },
  }));

  // KPI utama
  children.push(new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW/3), Math.floor(CW/3), CW - 2*Math.floor(CW/3)],
    rows: [new TableRow({ children: [
      { label:'SROI Blended',         value:ratio(sm.sroi_blended),             sub:'2023–2025' },
      { label:'Total Investasi',      value:idr(sm.total_investment_idr),       sub:'kumulatif' },
      { label:'Net Benefit Compounded',value:idr(sm.total_net_compounded_idr), sub:'terminal 2025' },
    ].map((item, i) => {
      const w = i < 2 ? Math.floor(CW/3) : CW - 2*Math.floor(CW/3);
      return new TableCell({
        children: [
          new Paragraph({ children:[runS(item.label,{color:C.teal})], spacing:{before:0,after:40} }),
          new Paragraph({ children:[new TextRun({text:item.value,font:'Arial',size:28,bold:true,color:C.navy})], spacing:{before:0,after:40} }),
          new Paragraph({ children:[runS(item.sub,{color:C.gray,italics:true})], spacing:{before:0,after:0} }),
        ],
        width:   { size:w, type:WidthType.DXA },
        borders: bAllN(),
        shading: { fill: i%2===0 ? C.bgTeal : C.bgBlue, type:ShadingType.CLEAR },
        margins: { top:160, bottom:160, left:180, right:180 },
      });
    })})]
  }));

  children.push(gap(200));
  children.push(new Paragraph({
    children: [run(
      `Program ${pi.program_name} menghasilkan SROI blended ${ratio(sm.sroi_blended)} selama periode ` +
      `${pi.period_start}–${pi.period_end} — artinya setiap Rp 1 yang diinvestasikan menghasilkan ` +
      `Rp ${Number(sm.sroi_blended).toFixed(2)} nilai sosial-ekonomi terukur. Program beroperasi di ` +
      `empat node dengan tiga node aktif bertransaksi, dan satu node eks-WBP (Milenial Motor) yang ` +
      `menjadi proof-of-concept reintegrasi produktif.`
    )],
    alignment: AlignmentType.JUSTIFIED, spacing: sp(0,160,340),
  }));
  children.push(new Paragraph({ children:[new PageBreak()] }));
  return children;
}

// ══════════════════════════════════════════════════════════════
// CHAPTER RENDERER (reuse dari Sprint 4 renderer.js logic)
// ══════════════════════════════════════════════════════════════
function hdrCell(text, width, bg=C.navy, textCol=C.white) {
  return new TableCell({
    children: [new Paragraph({
      children: [new TextRun({text, font:'Arial', size:18, bold:true, color:textCol})],
      alignment: AlignmentType.CENTER, spacing:{before:0,after:0},
    })],
    width:   { size:width, type:WidthType.DXA },
    borders: bAll(bg),
    shading: { fill:bg, type:ShadingType.CLEAR },
    margins: { top:80, bottom:80, left:100, right:100 },
  });
}

function calloutBlock(block) {
  const STYLES = {
    callout_info:    { bg:'EEF4FA', border:C.teal },
    callout_warning: { bg:'FDF5E8', border:C.amber },
    callout_success: { bg:'EAF5EE', border:C.green },
    callout_danger:  { bg:'FAEAEA', border:'C03040' },
    callout_neutral: { bg:'F4F4F4', border:C.grayLt },
    callout_gap:     { bg:'F4F4F4', border:'999999' },
  };
  const s = STYLES[block.type] || STYLES.callout_neutral;
  return new Table({
    width: { size:CW, type:WidthType.DXA },
    columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({
      children: [new Paragraph({
        children: [new TextRun({text:block.text||'',font:'Arial',size:20,color:'111111'})],
        alignment: AlignmentType.JUSTIFIED, spacing:{before:0,after:0},
      })],
      width:   { size:CW, type:WidthType.DXA },
      borders: { top:bdr(s.border,8), bottom:bdr(s.border,8), left:bdr(s.border,12), right:bdr(s.border,8) },
      shading: { fill:s.bg, type:ShadingType.CLEAR },
      margins: { top:140, bottom:140, left:220, right:220 },
    })]})],
  });
}

function metricCard(block) {
  const items = block.items || [];
  const cols  = items.length || 1;
  const w     = Math.floor(CW / cols);
  const widths = items.map((_,i) => i < cols-1 ? w : CW - w*(cols-1));
  return new Table({
    width: { size:CW, type:WidthType.DXA },
    columnWidths: widths,
    rows: [new TableRow({ children: items.map((item,i) =>
      new TableCell({
        children: [
          new Paragraph({ children:[runS(item.label||'',{color:C.teal})], spacing:{before:0,after:40} }),
          new Paragraph({ children:[new TextRun({text:item.value||'',font:'Arial',size:30,bold:true,color:C.navy})], spacing:{before:0,after:40} }),
          item.sublabel ? new Paragraph({ children:[runS(item.sublabel,{color:C.gray,italics:true})], spacing:{before:0,after:0} })
                        : new Paragraph({ children:[run('')], spacing:{before:0,after:0} }),
        ],
        width:   { size:widths[i], type:WidthType.DXA },
        borders: bAllN(),
        shading: { fill: i%2===0 ? C.bgTeal : C.bgBlue, type:ShadingType.CLEAR },
        margins: { top:160, bottom:160, left:180, right:180 },
      })
    )})]
  });
}

function tableBlock(block) {
  const headers = block.headers || [];
  const rows    = block.rows    || [];
  const cw      = block.column_widths || headers.map(()=>Math.floor(CW/Math.max(headers.length,1)));

  const hRow = new TableRow({
    children: headers.map((h,i) => hdrCell(String(h), cw[i])),
  });
  const isTotal = row => String(row[0]||'').toUpperCase().startsWith('TOTAL');

  const dRows = rows.map((row, ri) => {
    const tot = isTotal(row);
    const alt = ri%2===0;
    return new TableRow({ children: row.map((cell, ci) =>
      new TableCell({
        children: [new Paragraph({
          children: [new TextRun({
            text: String(cell??''), font:'Arial', size:19,
            bold: tot || ci===0, color: tot ? C.white : ci===0 ? C.navy : '111111',
          })],
          alignment: ci===0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
          spacing: {before:0,after:0},
        })],
        width:   { size:cw[ci], type:WidthType.DXA },
        borders: bAll(C.grayLt),
        shading: { fill: tot ? C.navy : alt ? 'EEF4FA' : 'FFFFFF', type:ShadingType.CLEAR },
        margins: { top:80, bottom:80, left:100, right:100 },
      })
    )});
  });

  const result = [new Table({ width:{size:CW,type:WidthType.DXA}, columnWidths:cw, rows:[hRow,...dRows] })];
  if (block.note) result.push(new Paragraph({ children:[runS(block.note,{italics:true,color:C.gray})], spacing:sp(60,120) }));
  return result;
}

function tableBorderless(block) {
  const headers = block.headers || [];
  const rows    = block.rows    || [];
  const cw      = block.column_widths || headers.map(()=>Math.floor(CW/Math.max(headers.length,1)));

  const bBot  = { top:bNone(),left:bNone(),right:bNone(), bottom:bdr(C.teal,8) };
  const bData = { top:bNone(),left:bNone(),right:bNone(), bottom:bdr(C.grayLt,2) };

  const hRow = new TableRow({ children: headers.map((h,i) => new TableCell({
    children: [new Paragraph({ children:[new TextRun({text:String(h),font:'Arial',size:18,bold:true,color:C.teal})], spacing:{before:0,after:0} })],
    width:{size:cw[i],type:WidthType.DXA}, borders:bBot, margins:{top:80,bottom:80,left:0,right:100},
  }))});

  const dRows = rows.map(row => new TableRow({ children: row.map((cell,ci) => new TableCell({
    children: [new Paragraph({ children:[new TextRun({text:String(cell??''),font:'Arial',size:20,bold:ci===0})], spacing:{before:0,after:0} })],
    width:{size:cw[ci],type:WidthType.DXA}, borders:bData, margins:{top:80,bottom:80,left:0,right:100},
  }))}));

  return [new Table({ width:{size:CW,type:WidthType.DXA}, columnWidths:cw, rows:[hRow,...dRows] })];
}

function barChart(block) {
  const points = block.data_points || [];
  const maxVal = block.max_value || 1;
  const rows = points.map(pt => {
    const pct    = Math.min(pt.value/maxVal, 1);
    const filled = Math.round(pct*35);
    const bar    = '█'.repeat(filled) + '░'.repeat(35-filled);
    return new Paragraph({
      children: [
        new TextRun({text:String(pt.label).padEnd(10), font:'Courier New', size:18}),
        new TextRun({text:bar+'  ', font:'Courier New', size:14, color:C.teal}),
        new TextRun({text:`${pt.value}`, font:'Arial', size:20, bold:true, color:C.navy}),
      ],
      spacing: {before:0,after:40},
    });
  });
  if (block.title) rows.unshift(new Paragraph({ children:[run(block.title,{bold:true,color:C.navy})], spacing:sp(80,60) }));
  return rows;
}

function renderBlock(block) {
  const t = block.type;
  switch(t) {
    case 'heading_1':
      return [new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun({text:block.text,font:'Arial',size:36,bold:true,color:C.navy})],
        spacing: sp(320,160),
        border:  { bottom:{style:BorderStyle.SINGLE,size:8,color:C.teal,space:4} },
      })];
    case 'heading_2':
      return [new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun({text:block.text,font:'Arial',size:26,bold:true,color:C.teal})],
        spacing: sp(240,100),
      })];
    case 'heading_3':
      return [new Paragraph({
        children: [new TextRun({text:block.text,font:'Arial',size:22,bold:true,color:C.navy})],
        spacing: sp(180,70),
      })];
    case 'paragraph_lead':
      return [new Paragraph({
        children:  [new TextRun({text:block.text,font:'Arial',size:26,color:'111111'})],
        alignment: AlignmentType.JUSTIFIED, spacing:sp(0,160,340),
      })];
    case 'paragraph':
      return [new Paragraph({
        children:  [new TextRun({text:block.text,font:'Arial',size:22})],
        alignment: AlignmentType.JUSTIFIED, spacing:sp(0,120,320),
      })];
    case 'paragraph_small':
      return [new Paragraph({
        children:  [runS(block.text,{italics:true,color:C.gray})],
        alignment: AlignmentType.JUSTIFIED, spacing:sp(0,80),
      })];
    case 'divider':
      return [new Paragraph({
        children:[run('')], spacing:{before:0,after:80},
        border:{ bottom:{style:BorderStyle.SINGLE,size:4,color:C.grayLt,space:4} },
      })];
    case 'divider_thick':
      return [new Paragraph({
        children:[run('')], spacing:{before:0,after:80},
        border:{ bottom:{style:BorderStyle.SINGLE,size:12,color:C.teal,space:4} },
      })];
    case 'divider_dashed':
      return [new Paragraph({
        children:[run('')], spacing:{before:0,after:80},
        border:{ bottom:{style:BorderStyle.DASHED,size:6,color:C.gray,space:4} },
      })];
    case 'page_break':
      return [new Paragraph({ children:[new PageBreak()] })];
    case 'callout_info': case 'callout_warning': case 'callout_success':
    case 'callout_danger': case 'callout_neutral': case 'callout_gap':
      return [calloutBlock(block), gap(100)];
    case 'metric_card_3col': case 'metric_card_4col': case 'metric_card_fullwidth':
      return [metricCard(block), gap(100)];
    case 'bar_chart_text':
      return [...barChart(block), gap(80)];
    case 'table': case 'table_total_row': case 'table_accent_col':
      return [...tableBlock(block), gap(80)];
    case 'table_borderless':
      return [...tableBorderless(block), gap(80)];
    case 'bullet_list':
      return (block.items||[]).map(item => new Paragraph({
        numbering: {reference:'bullets',level:0},
        children:  [run(item.text||String(item))],
        spacing:   sp(0,80,300),
      }));
    case 'numbered_list':
      return (block.items||[]).map(item => new Paragraph({
        numbering: {reference:'numbers',level:0},
        children:  [run(item.text||String(item))],
        spacing:   sp(0,80,300),
      }));
    case 'blockquote': case 'blockquote_accent':
      return [new Paragraph({
        children:  [new TextRun({text:block.text,font:'Arial',size:24,italics:true,color:C.navy})],
        indent:    {left:720,right:360}, alignment:AlignmentType.JUSTIFIED,
        spacing:   sp(80,120),
        border:    {left:{style:BorderStyle.SINGLE,size:16,color:C.teal,space:8}},
      })];
    default:
      return [calloutBlock({type:'callout_warning', text:`[Assembler] Block type tidak dikenal: "${t}"`}), gap(80)];
  }
}

// ══════════════════════════════════════════════════════════════
// RENDER SEMUA BAB
// ══════════════════════════════════════════════════════════════
function renderChapter(chapterData, isFirst=false) {
  const elements = [];
  // Page break sebelum setiap bab kecuali bab pertama
  if (!isFirst) {
    elements.push(new Paragraph({ children:[new PageBreak()] }));
  }
  for (const block of chapterData.blocks) {
    try {
      elements.push(...renderBlock(block));
    } catch(err) {
      elements.push(calloutBlock({type:'callout_warning', text:`[Error] ${block.type}: ${err.message}`}));
    }
  }
  return elements;
}

// ══════════════════════════════════════════════════════════════
// ASSEMBLE DOCUMENT
// ══════════════════════════════════════════════════════════════
console.log('\nBuilding document sections...');

const allChildren = [
  ...buildCoverPage(),
  ...buildVerificationPage(),
  ...buildKataPengantar(),
  ...buildRingkasanEksekutif(),
  ...buildTOC(),
];

// Render bab dalam urutan
let isFirstBab = true;
for (const babNum of BAB_ORDER) {
  if (!chaptersMap[babNum]) {
    console.warn(`  WARN: bab_${babNum} tidak ditemukan, dilewati`);
    continue;
  }
  const ch = chaptersMap[babNum];
  console.log(`  Rendering bab_${babNum}: ${ch.blocks.length} blocks`);
  allChildren.push(...renderChapter(ch, isFirstBab));
  isFirstBab = false;
}

console.log(`\nTotal elements: ${allChildren.length}`);

// ── SHARED HEADER & FOOTER ────────────────────────────────────
const sharedHeader = new Header({
  children: [new Paragraph({
    children: [
      new TextRun({text:`Laporan SROI  ·  ${pi.program_name}`, font:'Arial', size:16, color:C.teal}),
      new TextRun({text:'\t', font:'Arial', size:16}),
      new TextRun({text:pi.company, font:'Arial', size:16, color:C.gray}),
    ],
    tabStops: [{type:TabStopType.RIGHT, position:CW}],
    border:   {bottom:{style:BorderStyle.SINGLE,size:4,color:C.tealLt,space:4}},
    spacing:  {before:0,after:80},
  })],
});

const sharedFooter = new Footer({
  children: [new Paragraph({
    children: [
      new TextRun({text:`PT Dipa Konsultan Utama  ·  ${pi.period_end}`, font:'Arial', size:16, color:C.gray}),
      new TextRun({text:'\t', font:'Arial', size:16}),
      new TextRun({text:'Halaman ', font:'Arial', size:16, color:C.gray}),
    ],
    tabStops: [{type:TabStopType.RIGHT, position:CW}],
    border:   {top:{style:BorderStyle.SINGLE,size:4,color:C.grayLt,space:4}},
    spacing:  {before:80,after:0},
  })],
});

const doc = new Document({
  numbering: {
    config: [
      { reference:'bullets', levels:[{ level:0, format:LevelFormat.BULLET, text:'•', alignment:AlignmentType.LEFT,
          style:{ paragraph:{ indent:{left:560,hanging:280} } } }] },
      { reference:'numbers', levels:[{ level:0, format:LevelFormat.DECIMAL, text:'%1.', alignment:AlignmentType.LEFT,
          style:{ paragraph:{ indent:{left:560,hanging:280} } } }] },
    ],
  },
  styles: {
    default: { document: { run:{ font:'Arial', size:22 } } },
    paragraphStyles: [
      { id:'Heading1', name:'Heading 1', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:36, bold:true, color:C.navy, font:'Arial' },
        paragraph:{ spacing:{before:320,after:160}, outlineLevel:0 } },
      { id:'Heading2', name:'Heading 2', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:26, bold:true, color:C.teal, font:'Arial' },
        paragraph:{ spacing:{before:240,after:100}, outlineLevel:1 } },
      { id:'Heading3', name:'Heading 3', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:22, bold:true, color:C.navy, font:'Arial' },
        paragraph:{ spacing:{before:180,after:70}, outlineLevel:2 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size:   { width:11906, height:16838 },
        margin: { top:MARGIN, right:MARGIN, bottom:MARGIN, left:MARGIN },
        pageNumbers: { start:1, formatType:NumberFormat.DECIMAL },
      },
    },
    headers: { default: sharedHeader },
    footers: { default: sharedFooter },
    children: allChildren,
  }],
});

// ── WRITE ─────────────────────────────────────────────────────
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT_FILE, buf);
  const sizeMB = (buf.length / 1024 / 1024).toFixed(2);
  console.log(`\nOutput: ${path.resolve(OUTPUT_FILE)} (${sizeMB} MB)`);

  // Snapshot canonical
  const snapshotPath = path.join(path.dirname(OUTPUT_FILE), 'canonical_snapshot.json');
  fs.copyFileSync(CANONICAL_FILE, snapshotPath);
  console.log(`Snapshot: ${snapshotPath}`);

  console.log('\n' + '='.repeat(55));
  console.log('FULL ASSEMBLER COMPLETE');
  console.log(`  Bab assembled  : ${Object.keys(chaptersMap).length}`);
  console.log(`  Total blocks   : ${totalBlocks}`);
  console.log(`  Total elements : ${allChildren.length}`);
  console.log(`  File size      : ${sizeMB} MB`);
  console.log('='.repeat(55));
}).catch(err => {
  console.error('FAIL:', err.message);
  process.exit(1);
});
