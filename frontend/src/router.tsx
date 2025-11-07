import { BrowserRouter, Switch, Route } from 'react-router-dom';
import App from './App';
import { TermsOfService } from './pages/TermsOfService';
import { PrivacyPolicy } from './pages/PrivacyPolicy';
import { AccountManagement } from './pages/AccountManagement';
import { ProfilePage } from './pages/ProfilePage';
import { SettingsPage } from './pages/SettingsPage';
import { PaymentSuccess } from './pages/PaymentSuccess';
import { PaymentCancel } from './pages/PaymentCancel';
import { QuestionRenderPage } from './pages/QuestionRenderPage';
import { useAuth } from './contexts/AuthContext';

function AuthenticatedApp() {
  console.log('[AuthenticatedApp] Rendering');
  return <App />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Switch>
        <Route exact path="/" component={AuthenticatedApp} />
        <Route path="/question-render/:questionId" component={QuestionRenderPage} />
        <Route path="/terms-of-service" component={TermsOfService} />
        <Route path="/privacy-policy" component={PrivacyPolicy} />
        <Route path="/account" component={AccountManagement} />
        <Route path="/profile" component={ProfilePage} />
        <Route path="/settings" component={SettingsPage} />
        <Route path="/payment/success" component={PaymentSuccess} />
        <Route path="/payment/cancel" component={PaymentCancel} />
      </Switch>
    </BrowserRouter>
  );
}
