import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.aitutor.mobile',
  appName: 'AI Tutor',
  webDir: 'build',
  server: {
    androidScheme: 'http',
    allowNavigation: ['*.google.com', '*.googleapis.com'],
    cleartext: true
  },
  android: {
    allowMixedContent: true
  }
};

export default config;
