/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Switch, Redirect } from "react-router-dom";
import "./index.css";
import "./alignment-fix.css";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
// @ts-ignore
import "./package/perseus/testing/perseus-init.tsx";

// Suppress noisy Perseus library warnings that we cannot fix (upstream issues)
{
  const _origWarn = console.warn;
  const _origError = console.error;
  const SUPPRESSED = [
    'findDOMNode is deprecated',
    'A component is changing an uncontrolled',
    'A string ref',                // React: "A string ref, "%s", has been found..."
    'String refs are not supported', // React 18+ variant
    'deprecated and will be removed', // General deprecation pattern
    // NOTE: "is not accessible" REMOVED (Bug #69) — was hiding real a11y bugs
  ];
  const _filter = (orig: Function) => (...args: any[]) => {
    const msg = String(args[0] || '');
    if (SUPPRESSED.some(s => msg.includes(s))) return;
    orig.apply(console, args);
  };
  console.warn = _filter(_origWarn) as typeof console.warn;
  console.error = _filter(_origError) as typeof console.error;
}
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ThemeProvider } from "./components/theme/theme-provier";
import ComingSoonGuard from "./components/coming-soon/ComingSoonGuard"; // Commented out to allow home page access

const LoginPage = lazy(() => import("./components/auth/LoginPage"));
const LandingPageWrapper = lazy(() => import("./components/landing/LandingPageWrapper"));
const AccountPage = lazy(() => import("./components/account/AccountPage"));
const PricingPage = lazy(() => import("./components/pricing/PricingPage"));
const AssessmentFlow = lazy(() => import("./components/assessment/AssessmentFlow"));
const AssessmentExit = lazy(() => import("./components/assessment/AssessmentExit"));
const DevLogin = lazy(() => import("./components/auth/DevLogin"));
const AdminVideoPanel = lazy(() => import("./components/admin/AdminVideoPanel"));
const CostTrackingPage = lazy(() => import("./components/admin/CostTrackingPage"));

// Simple 404 page for unknown routes (Bug #42)
const NotFound: React.FC = () => (
  <div style={{
    position: 'fixed',
    inset: 0,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    background: '#FFFDF5',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    textAlign: 'center',
    padding: '20px'
  }}>
    <div style={{
      padding: '12px 24px',
      border: '4px solid #000',
      background: '#FF6B6B',
      color: '#fff',
      fontWeight: 900,
      fontSize: '48px',
      marginBottom: '24px',
      boxShadow: '4px 4px 0 #000'
    }}>
      404
    </div>
    <h1 style={{
      fontSize: '24px',
      fontWeight: 900,
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      marginBottom: '12px',
      color: '#000'
    }}>
      Page Not Found
    </h1>
    <p style={{
      fontSize: '14px',
      fontWeight: 600,
      color: '#666',
      marginBottom: '24px',
      maxWidth: '400px'
    }}>
      The page you're looking for doesn't exist or has been moved.
    </p>
    <button
      onClick={() => window.location.href = '/app'}
      style={{
        padding: '12px 32px',
        border: '3px solid #000',
        background: '#FFD93D',
        boxShadow: '3px 3px 0 #000',
        cursor: 'pointer',
        fontWeight: 900,
        fontSize: '14px',
        textTransform: 'uppercase',
        letterSpacing: '0.05em'
      }}
    >
      Go Home
    </button>
  </div>
);

// Guard against HMR re-creating the root (Bug #5)
const container = document.getElementById("root") as HTMLElement;
const root = (container as any).__reactRoot ||
  ((container as any).__reactRoot = ReactDOM.createRoot(container));

const queryClient = new QueryClient();

// Suppress Perseus library warnings (known issues in the library)
// NOTE (Bug #69): Only suppress truly benign upstream Perseus noise — do NOT suppress
// "Blocked aria-hidden" or a11y warnings, as those indicate real accessibility problems.
if (import.meta.env.DEV) {
  const originalWarn = console.warn;
  console.warn = (...args: any[]) => {
    const message = args[0]?.toString() || '';
    if (
      message.includes('findDOMNode is deprecated') ||
      message.includes('Multiple versions of @khanacademy')
    ) {
      return;
    }
    originalWarn.apply(console, args);
  };
}

// Component to decide between landing page and app
const LandingPageOrApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // If user just came from assessment, always show the App (not the landing page)
  const params = new URLSearchParams(window.location.search);
  const fromAssessment = params.get('fromAssessment') === '1';

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'var(--neo-bg, #FFFDF5)'
      }}>
        <div>Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated && !fromAssessment) {
    return <LandingPageWrapper />;
  }

  return <App />;
};

// Error boundary component for debugging
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          background: '#FFFDF5',
          padding: '20px',
          textAlign: 'center'
        }}>
          <h1 style={{ fontSize: '24px', fontWeight: 900, marginBottom: '16px' }}>Something went wrong</h1>
          <p style={{ fontSize: '14px', marginBottom: '8px' }}>{this.state.error?.message}</p>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '12px 24px',
              border: '4px solid #000000',
              background: '#FFD93D',
              cursor: 'pointer',
              fontWeight: 700,
              textTransform: 'uppercase'
            }}
          >
            Reload Page
          </button>
          <details style={{ marginTop: '20px', textAlign: 'left', maxWidth: '600px' }}>
            <summary style={{ cursor: 'pointer', marginBottom: '10px' }}>Error Details</summary>
            <pre style={{ background: '#f5f5f5', padding: '10px', overflow: 'auto', fontSize: '12px' }}>
              {this.state.error?.stack}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}

root.render(
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider defaultTheme="light" storageKey="ai-tutor-theme">
        <AuthProvider>
          <ComingSoonGuard>
            <Suspense fallback={
              <div style={{
                minHeight: '100vh',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '16px',
                background: '#FFFDF5',
                fontFamily: 'system-ui, -apple-system, sans-serif',
              }}>
                <div style={{
                  width: '200px',
                  height: '8px',
                  border: '3px solid #000',
                  backgroundColor: '#fff',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%',
                    width: '40%',
                    backgroundColor: '#FFD93D',
                    animation: 'suspense-loading-bar 1.5s ease-in-out infinite',
                  }} />
                </div>
                <div style={{
                  fontWeight: 900,
                  fontSize: '16px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#000',
                }}>
                  Loading...
                </div>
                <style>{`
                  @keyframes suspense-loading-bar {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(350%); }
                  }
                `}</style>
              </div>
            }>
              <Switch>
                <Route path="/app/dev-login" component={DevLogin} />
                <Route path="/app/auth/setup" component={LoginPage} />
                <Route path="/app/login" component={LoginPage} />
                <Route path="/app/account" component={AccountPage} />
                <Route path="/app/pricing" component={PricingPage} />
                <Route path="/pricing" component={PricingPage} />
                <Route path="/app/admin/videos" component={AdminVideoPanel} />
                <Route path="/app/admin/cost-tracking" component={CostTrackingPage} />
                <Route path="/app/assessment-exit" component={AssessmentExit} />
                <Route path="/app/assessment/:subject" component={AssessmentFlow} />
                <Route path="/app/learn/:subject" component={App} />
                <Route path="/landing/:id" component={LandingPageWrapper} /> {/* Dynamic landing page routes */}
                <Route path="/app/:profileId" component={LandingPageOrApp} />
                <Route path="/app" exact component={LandingPageOrApp} />
                <Route path="/" exact render={() => <Redirect to="/comingsoon" />} />
                <Route component={NotFound} /> {/* 404 catch-all (Bug #42) */}
              </Switch>
            </Suspense>
          </ComingSoonGuard>
        </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </ErrorBoundary>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals(console.log);
