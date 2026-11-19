import { apiBase } from './api-base';

describe('apiBase', () => {
  it('uses the dev API when served by ng serve on 4200', () => {
    expect(apiBase({ port: '4200', hostname: 'localhost' })).toBe('http://localhost:8000');
  });
  it('uses the same-origin /api path in a deployment on the default port', () => {
    expect(apiBase({ port: '', hostname: 'cerberus.example.com' })).toBe('/api');
  });
  it('uses /api on any other port too', () => {
    expect(apiBase({ port: '8080', hostname: 'localhost' })).toBe('/api');
  });
});
