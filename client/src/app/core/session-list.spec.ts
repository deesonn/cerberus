import { parseUtc, signedInAgo, timeLeft } from './session-list';

const NOW = new Date('2026-11-18T12:00:00Z');

describe('parseUtc', () => {
  it('treats a time with no zone as UTC', () => {
    expect(parseUtc('2026-11-18T12:00:00').getTime()).toBe(NOW.getTime());
  });
  it('leaves a time that already has a zone alone', () => {
    expect(parseUtc('2026-11-18T12:00:00Z').getTime()).toBe(NOW.getTime());
    expect(parseUtc('2026-11-18T07:00:00-05:00').getTime()).toBe(NOW.getTime());
  });
  it('copes with microseconds like the server sends', () => {
    expect(parseUtc('2026-11-18T12:00:00.123456').getTime()).toBeGreaterThanOrEqual(NOW.getTime());
  });
});

describe('signedInAgo', () => {
  it('says just now under a minute, and for times slightly in the future', () => {
    expect(signedInAgo('2026-11-18T11:59:40', NOW)).toBe('just now');
    expect(signedInAgo('2026-11-18T12:00:30', NOW)).toBe('just now');
  });
  it('uses minutes under an hour', () => {
    expect(signedInAgo('2026-11-18T11:48:00', NOW)).toBe('12 min ago');
  });
  it('uses hours under a day', () => {
    expect(signedInAgo('2026-11-18T09:00:00', NOW)).toBe('3 h ago');
  });
  it('uses days, singular and plural', () => {
    expect(signedInAgo('2026-11-17T11:00:00', NOW)).toBe('1 day ago');
    expect(signedInAgo('2026-11-15T12:00:00', NOW)).toBe('3 days ago');
  });
});

describe('timeLeft', () => {
  it('shows hours and minutes', () => {
    expect(timeLeft('2026-11-18T19:12:00', NOW)).toBe('7 h 12 min left');
  });
  it('drops the minutes when it is a whole number of hours', () => {
    expect(timeLeft('2026-11-18T20:00:00', NOW)).toBe('8 h left');
  });
  it('shows just minutes under an hour', () => {
    expect(timeLeft('2026-11-18T12:45:00', NOW)).toBe('45 min left');
  });
  it('says less than a minute for the last seconds', () => {
    expect(timeLeft('2026-11-18T12:00:30', NOW)).toBe('less than a minute left');
  });
  it('says expired once the time has passed', () => {
    expect(timeLeft('2026-11-18T11:59:00', NOW)).toBe('expired');
  });
});
