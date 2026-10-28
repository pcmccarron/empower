function validateStatsigClientKey(clientKey) {
  if (!clientKey || clientKey === 'client-local') {
    throw new Error('REACT_APP_STATSIG_CLIENT_KEY must be configured with a real Statsig client key');
  }
}

if (require.main === module) {
  validateStatsigClientKey(process.env.REACT_APP_STATSIG_CLIENT_KEY);
}

module.exports = validateStatsigClientKey;
