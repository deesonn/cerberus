import { cleanFilename, filterFiles, formatBytes, percentUsed, sortFiles } from './file-list';
import { FileMeta } from './files.service';

const f = (filename: string, size: number, uploaded_at: string): FileMeta => ({ hash: filename, filename, size, uploaded_at });
const SAMPLE = [
  f('Taxes-2025.pdf', 3000, '2026-11-01T10:00:00'),
  f('notes.txt', 40, '2026-11-03T10:00:00'),
  f('Budget.xlsx', 90000, '2026-11-02T10:00:00'),
];

describe('formatBytes', () => {
  it('handles zero and small values', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(512)).toBe('512 B');
  });
  it('scales to KB and MB with one decimal under 10', () => {
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(25 * 1024 * 1024)).toBe('25 MB');
  });
  it('treats bad input as zero', () => {
    expect(formatBytes(-5)).toBe('0 B');
    expect(formatBytes(NaN)).toBe('0 B');
  });
});

describe('filterFiles', () => {
  it('matches part of a name, ignoring case', () => {
    expect(filterFiles(SAMPLE, 'TAX').map((x) => x.filename)).toEqual(['Taxes-2025.pdf']);
  });
  it('matches in the middle of a name, not just the start', () => {
    expect(filterFiles(SAMPLE, '2025').map((x) => x.filename)).toEqual(['Taxes-2025.pdf']);
  });
  it('returns everything for a blank search', () => {
    expect(filterFiles(SAMPLE, '   ').length).toBe(3);
  });
  it('returns nothing when no name matches', () => {
    expect(filterFiles(SAMPLE, 'zzz')).toEqual([]);
  });
  it('does not modify the original list', () => {
    const copy = SAMPLE.slice();
    filterFiles(SAMPLE, 'notes');
    expect(SAMPLE).toEqual(copy);
  });
});

describe('sortFiles', () => {
  it('newest first by default', () => {
    expect(sortFiles(SAMPLE, 'newest').map((x) => x.filename)).toEqual(['notes.txt', 'Budget.xlsx', 'Taxes-2025.pdf']);
  });
  it('oldest first', () => {
    expect(sortFiles(SAMPLE, 'oldest').map((x) => x.filename)).toEqual(['Taxes-2025.pdf', 'Budget.xlsx', 'notes.txt']);
  });
  it('by name, ignoring case', () => {
    expect(sortFiles(SAMPLE, 'name').map((x) => x.filename)).toEqual(['Budget.xlsx', 'notes.txt', 'Taxes-2025.pdf']);
  });
  it('largest first by size', () => {
    expect(sortFiles(SAMPLE, 'size').map((x) => x.filename)).toEqual(['Budget.xlsx', 'Taxes-2025.pdf', 'notes.txt']);
  });
  it('does not modify the original list', () => {
    const before = SAMPLE.map((x) => x.filename);
    sortFiles(SAMPLE, 'name');
    expect(SAMPLE.map((x) => x.filename)).toEqual(before);
  });
});

describe('percentUsed', () => {
  it('rounds and clamps', () => {
    expect(percentUsed(50, 200)).toBe(25);
    expect(percentUsed(500, 200)).toBe(100);
    expect(percentUsed(-1, 200)).toBe(0);
  });
  it('is safe with a zero quota', () => {
    expect(percentUsed(10, 0)).toBe(0);
  });
});

describe('cleanFilename', () => {
  it('trims spaces around a good name', () => {
    expect(cleanFilename('  tax return.pdf ')).toEqual({ ok: true, value: 'tax return.pdf' });
  });
  it('refuses an empty or blank name', () => {
    expect(cleanFilename('').ok).toBeFalse();
    expect(cleanFilename('    ').ok).toBeFalse();
  });
  it('refuses forward and back slashes', () => {
    expect(cleanFilename('a/b.txt').ok).toBeFalse();
    expect(cleanFilename('a\\b.txt').ok).toBeFalse();
  });
  it('refuses control characters such as a newline', () => {
    expect(cleanFilename('bad\nname').ok).toBeFalse();
  });
  it('allows exactly 255 characters but not 256', () => {
    expect(cleanFilename('a'.repeat(255)).ok).toBeTrue();
    expect(cleanFilename('a'.repeat(256)).ok).toBeFalse();
  });
  it('gives a readable message when refusing', () => {
    const r = cleanFilename('');
    expect(r.ok === false && r.error.length > 0).toBeTrue();
  });
});
