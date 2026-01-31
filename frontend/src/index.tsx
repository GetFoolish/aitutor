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
import App from "./App";
import reportWebVitals from "./reportWebVitals";
// @ts-ignore
import "./package/perseus/testing/perseus-init.tsx";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import ComingSoonGuard from "./components/coming-soon/ComingSoonGuard"; // Commented out to allow home page access

const LoginPage = lazy(() => import("./components/auth/LoginPage"));
const LandingPageWrapper = lazy(() => import("./components/landing/LandingPageWrapper"));
const AccountPage = lazy(() => import("./components/account/AccountPage"));
const PricingPage = lazy(() => import("./components/pricing/PricingPage"));
const AssessmentFlow = lazy(() => import("./components/assessment/AssessmentFlow"));
const DynamicAssessment = lazy(() => import("./components/assessment/DynamicAssessment"));
const AdminVideoPanel = lazy(() => import("./components/admin/AdminVideoPanel"));
const CostTrackingPage = lazy(() => import("./components/admin/CostTrackingPage"));
const LearningPlanDashboard = lazy(() => import("./components/learning-plan/LearningPlanDashboard"));
const PracticeSession = lazy(() => import("./components/practice/PracticeSession"));
const LearnerOnboarding = lazy(() => import("./components/onboarding/LearnerOnboarding"));

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement,
);

const queryClient = new QueryClient();

// Suppress Perseus library warnings (known issues in the library)
if (import.meta.env.DEV) {
  const originalWarn = console.warn;
  console.warn = (...args: any[]) => {
    // Filter out known Perseus warnings
    const message = args[0]?.toString() || '';
    if (
      message.includes('findDOMNode is deprecated') ||
      message.includes('Multiple versions of @khanacademy') ||
      message.includes('Blocked aria-hidden')
    ) {
      return; // Suppress these warnings
    }
    originalWarn.apply(console, args);
  };
}

// Component to decide between landing page and app
const LandingPageOrApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

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

  if (!isAuthenticated) {
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
          background: '#FFFFFF',
          padding: '20px',
          textAlign: 'center'
        }}>
          {/* EXTREME NEO-BRUTALISM Error Card */}
          <div style={{
            background: '#FF6B6B',
            border: '5px solid #000000',
            padding: '48px',
            maxWidth: '500px',
            boxShadow: '8px 8px 0px 0px #000000'
          }}>
            <div style={{ fontSize: '64px', marginBottom: '24px' }}>⚠️</div>
            <h1 style={{
              fontSize: '32px',
              fontWeight: 900,
              marginBottom: '16px',
              textTransform: 'uppercase',
              fontFamily: 'Space Mono, monospace',
              color: '#000000'
            }}>
              SOMETHING WENT WRONG
            </h1>
            <p style={{
              fontSize: '16px',
              fontWeight: 700,
              marginBottom: '24px',
              color: '#000000'
            }}>
              {this.state.error?.message}
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '16px 32px',
                border: '4px solid #000000',
                background: '#FCD34D',
                cursor: 'pointer',
                fontWeight: 900,
                textTransform: 'uppercase',
                fontSize: '18px',
                fontFamily: 'Space Mono, monospace',
                boxShadow: '4px 4px 0px 0px #000000'
              }}
            >
              RELOAD PAGE
            </button>
          </div>
          <details style={{
            marginTop: '24px',
            textAlign: 'left',
            maxWidth: '600px',
            background: '#FFFFFF',
            border: '3px solid #000000',
            padding: '16px',
            boxShadow: '4px 4px 0px 0px #000000'
          }}>
            <summary style={{
              cursor: 'pointer',
              marginBottom: '10px',
              fontWeight: 700,
              textTransform: 'uppercase'
            }}>
              ERROR DETAILS
            </summary>
            <pre style={{
              background: '#FCD34D',
              padding: '16px',
              overflow: 'auto',
              fontSize: '12px',
              fontFamily: 'Space Mono, monospace',
              border: '2px solid #000000'
            }}>
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
        <AuthProvider>
          <ComingSoonGuard>
            <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
              <Switch>
                <Route path="/app/auth/setup" component={LoginPage} />
                <Route path="/app/login" component={LoginPage} />
                <Route path="/app/admin/videos" component={AdminVideoPanel} />
                <Route path="/app/admin/cost-tracking" component={CostTrackingPage} />
                <Route path="/app/onboarding" component={LearnerOnboarding} />
                <Route path="/app/learning-plan" component={LearningPlanDashboard} />
                <Route path="/app/practice" component={PracticeSession} />
                <Route path="/app/assessment/dynamic" component={DynamicAssessment} />
                <Route path="/app/assessment/:subject" render={() => <Redirect to="/app/onboarding" />} />
                <Route path="/app/account" component={AccountPage} />
                <Route path="/app/pricing" component={PricingPage} />
                <Route path="/pricing" component={PricingPage} />
                <Route path="/assessment/:subject" render={() => <Redirect to="/app/onboarding" />} />
                <Route path="/assessment" exact render={() => <Redirect to="/app/onboarding" />} />
                <Route path="/landing/:id" component={LandingPageWrapper} /> {/* Dynamic landing page routes */}
                <Route path="/app" exact component={LandingPageOrApp} />
                <Route path="/app" component={App} />
                <Route path="/" exact render={() => <Redirect to="/comingsoon" />} />
                <Route component={LandingPageOrApp} /> {/* Catch-all route - fallback to landing page */}
              </Switch>
            </Suspense>
          </ComingSoonGuard>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </ErrorBoundary>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals(console.log);
