const validateStatsigClientKey = require('../../scripts/validate-statsig-client-key');

describe('Statsig client key validation', () => {
  it.each([undefined, '', 'client-local'])('rejects invalid key %s', (clientKey) => {
    expect(() => validateStatsigClientKey(clientKey)).toThrow(
      'REACT_APP_STATSIG_CLIENT_KEY must be configured with a real Statsig client key'
    );
  });

  it('accepts a configured client key', () => {
    expect(() => validateStatsigClientKey('client-test-key')).not.toThrow();
  });
});
