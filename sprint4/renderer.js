/**
 * Renderer — Sprint 4
 * SROI Report System
 *
 * Input : chapter_semantic_bab7.json (Handoff E dari QA / Narrative Builder)
 * Output: ESL_Report_Bab7.docx
 *
 * Usage:
 *   node renderer.js
 *   node renderer.js --semantic /p/chapter_semantic_bab7.json --output /p/ESL_Report_Bab7.docx
 *   SEMANTIC_FILE=... OUTPUT_FILE=... node renderer.js
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, LevelFormat, TabStopType, PageBreak
} = require('docx');
const fs   = require('fs');
const path = require('path');

// ── PATH CONFIG ──────────────────────────────────────────────
const args = process.argv.slice(2);
const argMap = {};
for (let i = 0; i < args.length; i += 2) {
  if (args[i].startsWith('--')) argMap[args[i].slice(2)] = args[i+1];
}

const SCRIPT_DIR   = __dirname;
const SEMANTIC_FILE = argMap['semantic']
  || process.env.SEMANTIC_FILE
  || path.join(SCRIPT_DIR, '../sprint3/chapter_semantic_bab7.json');

// Output filename dinamis dari program_code — tidak hardcode ESL
const _rawSemantic = JSON.parse(fs.readFileSync(SEMANTIC_FILE, 'utf8'));
const _bab7Preview = Array.isArray(_rawSemantic) ? _rawSemantic[0] : _rawSemantic;
const _progCode    = _bab7Preview.program_code || 'PROGRAM';

const OUTPUT_FILE = argMap['output']
  || process.env.OUTPUT_FILE
  || path.join(SCRIPT_DIR, `${_progCode}_Report_Bab7.docx`);

console.log(`Semantic  : ${path.resolve(SEMANTIC_FILE)}`);
console.log(`Output    : ${path.resolve(OUTPUT_FILE)}`);

const semanticRaw = JSON.parse(fs.readFileSync(SEMANTIC_FILE, 'utf8'));
const semantic    = Array.isArray(semanticRaw) ? semanticRaw : [semanticRaw];
const bab7        = semantic.find(b => b.chapter_id === 'bab_7');
if (!bab7) { console.error('FAIL: bab_7 tidak ditemukan'); process.exit(1); }

// ── COLOUR PALETTE (Marine Teal) ────────────────────────────
const C = {
  navy:    '0D2B2B', navyMid: '1A4040', teal:   '0A6B6B',
  tealLt:  '00B4B4', orange: 'E8541A', amber:  'E67E22',
  green:   '1A7A50', greenLt:'27B872', red:    'C03040',
  white:   'FFFFFF', gray:   '555555', grayLt: 'CCCCCC',
  bgBlue:  'EEF4FA', bgTeal: 'EAF5F5', bgGreen:'EAF5EE',
  bgWarm:  'FDF5E8', bgRed:  'FAEAEA', bgGray:  'F4F4F4',
};

// ── CONSTANTS ─────────────────────────────────────────────────
const MARGIN = 1134;                    // ~0.79 inch
const CW     = 11906 - 2 * MARGIN;     // 9638 DXA content width

// ── BORDER HELPERS ────────────────────────────────────────────
const bdr  = (col = C.grayLt, sz = 4) => ({ style: BorderStyle.SINGLE, size: sz, color: col });
const bAll = (col = C.grayLt)          => ({ top: bdr(col), bottom: bdr(col), left: bdr(col), right: bdr(col) });
const bNone= ()                         => ({ style: BorderStyle.NONE, size: 0, color: 'FFFFFF' });
const bAllN= ()                         => ({ top: bNone(), bottom: bNone(), left: bNone(), right: bNone() });

// ── TEXT RUN HELPERS ─────────────────────────────────────────
const run  = (text, opts = {}) => new TextRun({ text, font: 'Arial', size: 22, ...opts });
const runS = (text, opts = {}) => new TextRun({ text, font: 'Arial', size: 18, ...opts });
const runM = (text, opts = {}) => new TextRun({ text, font: 'Courier New', size: 20, ...opts });

// ── PARAGRAPH HELPERS ─────────────────────────────────────────
const sp = (bf = 0, af = 120, ln = 320) => ({ before: bf, after: af, line: ln });

function makeP(children, opts = {}) {
  return new Paragraph({
    children,
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing:   opts.spacing || sp(),
    ...opts.extra || {},
  });
}

function bullet(text, ref = 'bullets') {
  return new Paragraph({
    numbering:  { reference: ref, level: 0 },
    children:   [run(text)],
    spacing:    sp(0, 80, 300),
  });
}

function gap(pts = 100) {
  return new Paragraph({ children: [run('')], spacing: { before: 0, after: pts } });
}

// ── CELL HELPER ───────────────────────────────────────────────
function cell(children, opts = {}) {
  const paras = Array.isArray(children) ? children : [
    new Paragraph({
      children: [new TextRun({
        text:   children,
        font:   'Arial',
        size:   opts.size   || 20,
        bold:   opts.bold   || false,
        color:  opts.color  || '000000',
        italics:opts.italic || false,
      })],
      alignment: opts.align || AlignmentType.LEFT,
      spacing:   { before: 0, after: 0 },
    })
  ];
  return new TableCell({
    children,
    width:   { size: opts.width || 2000, type: WidthType.DXA },
    borders: opts.borders || bAll(C.grayLt),
    shading: opts.bg ? { fill: opts.bg, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: opts.valign || VerticalAlign.TOP,
  });
}

function hdrCell(text, width, bg = C.navy, textCol = C.white) {
  return new TableCell({
    children: [new Paragraph({
      children:  [new TextRun({ text, font: 'Arial', size: 18, bold: true, color: textCol })],
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 0 },
    })],
    width:   { size: width, type: WidthType.DXA },
    borders: bAll(bg),
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
  });
}

// ── CALLOUT BOX ───────────────────────────────────────────────
const CALLOUT_STYLES = {
  callout_info:    { bg: C.bgBlue,  border: C.teal,   icon: 'ℹ',  labelCol: C.teal   },
  callout_warning: { bg: C.bgWarm,  border: C.amber,  icon: '⚠',  labelCol: C.amber  },
  callout_success: { bg: C.bgGreen, border: C.green,  icon: '✓',  labelCol: C.green  },
  callout_danger:  { bg: C.bgRed,   border: C.red,    icon: '✕',  labelCol: C.red    },
  callout_neutral: { bg: C.bgGray,  border: C.grayLt, icon: '→',  labelCol: C.gray   },
  callout_gap:     { bg: C.bgGray,  border: '999999', icon: '◻',  labelCol: C.gray   },
};

function calloutBlock(block) {
  const style = CALLOUT_STYLES[block.type] || CALLOUT_STYLES.callout_neutral;
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({
      children: [
        new Paragraph({
          children: [new TextRun({ text: block.text, font: 'Arial', size: 20, color: '111111' })],
          alignment: AlignmentType.JUSTIFIED,
          spacing: { before: 0, after: 0 },
        }),
      ],
      width:   { size: CW, type: WidthType.DXA },
      borders: { top: bdr(style.border,8), bottom: bdr(style.border,8), left: bdr(style.border,12), right: bdr(style.border,8) },
      shading: { fill: style.bg, type: ShadingType.CLEAR },
      margins: { top: 140, bottom: 140, left: 220, right: 220 },
    })]})],
  });
}

// ── METRIC CARD ───────────────────────────────────────────────
function metricCard(block) {
  const items  = block.items || [];
  const cols   = items.length;
  const w      = Math.floor(CW / cols);
  const widths = items.map((_, i) => i < cols - 1 ? w : CW - w * (cols - 1));

  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: widths,
    rows: [new TableRow({ children: items.map((item, i) =>
      new TableCell({
        children: [
          new Paragraph({ children: [runS(item.label || '', { color: C.teal })], spacing: { before: 0, after: 40 } }),
          new Paragraph({ children: [new TextRun({ text: item.value || '', font: 'Arial', size: 32, bold: true, color: C.navy })], spacing: { before: 0, after: 40 } }),
          item.sublabel ? new Paragraph({ children: [runS(item.sublabel, { color: C.gray, italics: true })], spacing: { before: 0, after: 0 } }) : new Paragraph({ children: [run('')], spacing: { before: 0, after: 0 } }),
        ],
        width:   { size: widths[i], type: WidthType.DXA },
        borders: bAllN(),
        shading: { fill: i % 2 === 0 ? C.bgTeal : C.bgBlue, type: ShadingType.CLEAR },
        margins: { top: 160, bottom: 160, left: 180, right: 180 },
      })
    )})]
  });
}

// ── BAR CHART (text-based) ────────────────────────────────────
function barChart(block) {
  const points   = block.data_points || [];
  const maxVal   = block.max_value   || 1;
  const rows = points.map(pt => {
    const pct    = Math.min(pt.value / maxVal, 1);
    const filled = Math.round(pct * 35);
    const bar    = '█'.repeat(filled) + '░'.repeat(35 - filled);
    return new Paragraph({
      children: [
        runM(String(pt.label).padEnd(10), { size: 18 }),
        new TextRun({ text: bar + '  ', font: 'Courier New', size: 14, color: C.teal }),
        new TextRun({ text: `${pt.value}`, font: 'Arial', size: 20, bold: true, color: C.navy }),
      ],
      spacing: { before: 0, after: 40 },
    });
  });
  if (block.title) {
    rows.unshift(new Paragraph({ children: [run(block.title, { bold: true, color: C.navy })], spacing: sp(80, 60) }));
  }
  return rows;
}

// ── TABLE RENDERER ────────────────────────────────────────────
function tableBlock(block) {
  const headers = block.headers || [];
  const rows    = block.rows    || [];
  const cw      = block.column_widths || headers.map(() => Math.floor(CW / headers.length));
  const isTotal = (row) => row[0] && String(row[0]).toUpperCase().startsWith('TOTAL');

  const headerRow = new TableRow({
    children: headers.map((h, i) => hdrCell(String(h), cw[i])),
  });

  const dataRows = rows.map((row, ri) => {
    const isTot = isTotal(row);
    const alt   = ri % 2 === 0;
    return new TableRow({
      children: row.map((cell_text, ci) => {
        const isFirst = ci === 0;
        const text    = String(cell_text ?? '');
        const bg      = isTot ? C.navy : (alt ? C.bgBlue : 'FFFFFF');
        const col     = isTot ? C.white : (isFirst && !isTot ? C.navy : '111111');
        const bold    = isTot || isFirst;
        return new TableCell({
          children: [new Paragraph({
            children: [new TextRun({ text, font: 'Arial', size: 19, bold, color: col })],
            alignment: ci === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
            spacing: { before: 0, after: 0 },
          })],
          width:   { size: cw[ci], type: WidthType.DXA },
          borders: bAll(C.grayLt),
          shading: { fill: bg, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 100, right: 100 },
        });
      }),
    });
  });

  const result = [new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: cw, rows: [headerRow, ...dataRows] })];
  if (block.note) {
    result.push(new Paragraph({ children: [runS(block.note, { italics: true, color: C.gray })], spacing: sp(60, 120) }));
  }
  return result;
}

// ── TABLE BORDERLESS ──────────────────────────────────────────
function tableBorderless(block) {
  const headers = block.headers || [];
  const rows    = block.rows    || [];
  const cw      = block.column_widths || headers.map(() => Math.floor(CW / headers.length));

  const bBot  = { top: bNone(), left: bNone(), right: bNone(), bottom: bdr(C.teal, 8) };
  const bData = { top: bNone(), left: bNone(), right: bNone(), bottom: bdr(C.grayLt, 2) };

  const hRow = new TableRow({
    children: headers.map((h, i) => new TableCell({
      children: [new Paragraph({ children: [new TextRun({ text: String(h), font: 'Arial', size: 18, bold: true, color: C.teal })], spacing: { before: 0, after: 0 } })],
      width: { size: cw[i], type: WidthType.DXA }, borders: bBot, margins: { top: 80, bottom: 80, left: 0, right: 100 },
    })),
  });

  const dRows = rows.map(row => new TableRow({
    children: row.map((cell_text, ci) => new TableCell({
      children: [new Paragraph({ children: [new TextRun({ text: String(cell_text ?? ''), font: 'Arial', size: 20, bold: ci === 0 })], spacing: { before: 0, after: 0 } })],
      width: { size: cw[ci], type: WidthType.DXA }, borders: bData, margins: { top: 80, bottom: 80, left: 0, right: 100 },
    })),
  }));

  return [new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: cw, rows: [hRow, ...dRows] })];
}

// ══════════════════════════════════════════════════════════════
// MAIN BLOCK RENDERER
// ══════════════════════════════════════════════════════════════

const RENDER_LOG = [];
function log(type, note = '') { RENDER_LOG.push({ type, note }); }

function renderBlock(block) {
  const type = block.type;
  log(type);

  switch (type) {

    case 'heading_1':
      return [new Paragraph({
        heading:  HeadingLevel.HEADING_1,
        children: [new TextRun({ text: block.text, font: 'Arial', size: 36, bold: true, color: C.navy })],
        spacing:  sp(320, 160),
        border:   { bottom: { style: BorderStyle.SINGLE, size: 8, color: C.teal, space: 4 } },
      })];

    case 'heading_2':
      return [new Paragraph({
        heading:  HeadingLevel.HEADING_2,
        children: [new TextRun({ text: block.text, font: 'Arial', size: 26, bold: true, color: C.teal })],
        spacing:  sp(240, 100),
      })];

    case 'heading_3':
      return [new Paragraph({
        children: [new TextRun({ text: block.text, font: 'Arial', size: 22, bold: true, color: C.navy })],
        spacing:  sp(180, 70),
      })];

    case 'paragraph_lead':
      return [new Paragraph({
        children:  [new TextRun({ text: block.text, font: 'Arial', size: 26, color: '111111' })],
        alignment: AlignmentType.JUSTIFIED,
        spacing:   sp(0, 160, 340),
      })];

    case 'paragraph':
      return [new Paragraph({
        children:  [new TextRun({ text: block.text, font: 'Arial', size: 22 })],
        alignment: AlignmentType.JUSTIFIED,
        spacing:   sp(0, 120, 320),
      })];

    case 'paragraph_small':
      return [new Paragraph({
        children:  [runS(block.text, { italics: true, color: C.gray })],
        alignment: AlignmentType.JUSTIFIED,
        spacing:   sp(0, 80),
      })];

    case 'paragraph_mono':
      return [new Paragraph({
        children:  [runM(block.text, { color: C.teal })],
        spacing:   sp(40, 120),
      })];

    case 'divider':
      return [new Paragraph({
        children: [run('')],
        spacing:  { before: 0, after: 80 },
        border:   { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.grayLt, space: 4 } },
      })];

    case 'divider_thick':
      return [new Paragraph({
        children: [run('')],
        spacing:  { before: 0, after: 80 },
        border:   { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.teal, space: 4 } },
      })];

    case 'divider_dashed':
      return [new Paragraph({
        children: [run('')],
        spacing:  { before: 0, after: 80 },
        border:   { bottom: { style: BorderStyle.DASHED, size: 6, color: C.gray, space: 4 } },
      })];

    case 'page_break':
      return [new Paragraph({ children: [new PageBreak()] })];

    case 'callout_info':
    case 'callout_warning':
    case 'callout_success':
    case 'callout_danger':
    case 'callout_neutral':
    case 'callout_gap':
      return [calloutBlock(block), gap(100)];

    case 'metric_card_3col':
    case 'metric_card_4col':
    case 'metric_card_fullwidth':
      return [metricCard(block), gap(100)];

    case 'bar_chart_text':
      return [...barChart(block), gap(80)];

    case 'table':
      return [...tableBlock(block), gap(80)];

    case 'table_borderless':
      return [...tableBorderless(block), gap(80)];

    case 'table_accent_col':
      return [...tableBlock(block), gap(80)]; // fallback ke tabel biasa

    case 'bullet_list':
      return (block.items || []).map(item => bullet(item.text || String(item)));

    case 'numbered_list':
      return (block.items || []).map(item => new Paragraph({
        numbering: { reference: 'numbers', level: 0 },
        children:  [run(item.text || String(item))],
        spacing:   sp(0, 80, 300),
      }));

    case 'blockquote':
    case 'blockquote_accent':
      return [new Paragraph({
        children:  [new TextRun({ text: block.text, font: 'Arial', size: 24, italics: true, color: C.navy })],
        indent:    { left: 720, right: 360 },
        alignment: AlignmentType.JUSTIFIED,
        spacing:   sp(80, 120),
        border:    { left: { style: BorderStyle.SINGLE, size: 16, color: C.teal, space: 8 } },
      })];

    default:
      log(type, 'UNKNOWN — rendered as warning callout');
      return [calloutBlock({
        type: 'callout_warning',
        text: `[Renderer] Block type tidak dikenal: "${type}" — konten tidak dirender.`,
      }), gap(80)];
  }
}

// ══════════════════════════════════════════════════════════════
// RENDER SEMUA BLOCKS
// ══════════════════════════════════════════════════════════════

console.log(`\nRendering ${bab7.blocks.length} blocks...`);
const children = [];

for (const block of bab7.blocks) {
  try {
    const rendered = renderBlock(block);
    children.push(...rendered);
  } catch (err) {
    console.error(`  ERROR on block [${block.type}]: ${err.message}`);
    children.push(calloutBlock({
      type: 'callout_warning',
      text: `[Renderer Error] ${block.type}: ${err.message}`,
    }));
  }
}

console.log(`  ${children.length} docx elements generated`);

// ══════════════════════════════════════════════════════════════
// ASSEMBLE DOCUMENT
// ══════════════════════════════════════════════════════════════

const doc = new Document({
  numbering: {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] },
      { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] },
    ],
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, color: C.navy, font: 'Arial' },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, color: C.teal, font: 'Arial' },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, color: C.navy, font: 'Arial' },
        paragraph: { spacing: { before: 180, after: 70 }, outlineLevel: 2 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size:   { width: 11906, height: 16838 },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: `Laporan Evaluasi SROI  ·  ${_progCode}  ·  Bab VII`, font: 'Arial', size: 16, color: C.teal }),
            new TextRun({ text: '\t', font: 'Arial', size: 16 }),
            new TextRun({ text: 'PT Dipa Konsultan Utama', font: 'Arial', size: 16, color: C.gray }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: CW }],
          border:   { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.tealLt || '00B4B4', space: 4 } },
          spacing:  { before: 0, after: 80 },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: 'PT Pertamina Lubricants  ·  Program TJSL CSV', font: 'Arial', size: 16, color: C.gray }),
            new TextRun({ text: '\t', font: 'Arial', size: 16 }),
            new TextRun({ text: 'Rendered by SROI Report System v1.0', font: 'Arial', size: 16, color: C.gray, italics: true }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: CW }],
          border:   { top: { style: BorderStyle.SINGLE, size: 4, color: C.grayLt, space: 4 } },
          spacing:  { before: 80, after: 0 },
        })],
      }),
    },
    children,
  }],
});

// ── WRITE ──────────────────────────────────────────────────────
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT_FILE, buf);
  console.log(`\nOutput: ${path.resolve(OUTPUT_FILE)}`);

  // Summary
  const typeCounts = {};
  RENDER_LOG.forEach(e => { typeCounts[e.type] = (typeCounts[e.type] || 0) + 1; });
  console.log('\n' + '='.repeat(55));
  console.log('RENDERER COMPLETE');
  console.log(`  Input blocks  : ${bab7.blocks.length}`);
  console.log(`  docx elements : ${children.length}`);
  console.log(`  Block types rendered:`);
  Object.entries(typeCounts).sort((a,b) => b[1]-a[1]).forEach(([t,n]) => {
    console.log(`    ${t.padEnd(30)} × ${n}`);
  });
  console.log('='.repeat(55));
  // Opsi A: snapshot semantic ke output dir untuk self-contained validation
  const semanticSnapshot = path.join(path.dirname(OUTPUT_FILE), 'chapter_semantic_bab7.json');
  fs.copyFileSync(SEMANTIC_FILE, semanticSnapshot);
  console.log(`Snapshot: ${path.resolve(semanticSnapshot)}`);

}).catch(err => {
  console.error('FAIL:', err.message);
  process.exit(1);
});
