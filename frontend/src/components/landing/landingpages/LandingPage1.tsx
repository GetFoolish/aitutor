/**
 * Landing Page 1: "The Tutor Who Actually Gives a Damn"
 * Clean, minimal design inspired by modern SaaS aesthetic
 */
import React, { useState } from 'react';
import { Brain, Eye, Heart, Star, ChevronDown, Check } from 'lucide-react';
import TeachrLogo from '../TeachrLogo';
import BackgroundShapes from '../../background-shapes/BackgroundShapes';
import '../landing.scss';

interface LandingPage1Props {
  onGetStarted: () => void;
}

const LandingPage1: React.FC<LandingPage1Props> = ({ onGetStarted }) => {
  const [openFAQ, setOpenFAQ] = useState<number | null>(null);

  return (
    <div className="landing-page landing-page-1">
      <BackgroundShapes count={30} />
      {/* Header */}
      <header className="lp1-header">
        <div className="lp1-container">
          <div onClick={() => window.location.href = '/'} style={{ cursor: 'pointer' }}>
            <TeachrLogo size="large" />
          </div>
          <nav className="lp1-nav">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <button onClick={onGetStarted} className="lp1-btn-header">Start Free Trial</button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="lp1-hero">
        <div className="lp1-container">
          <div className="lp1-hero-split">
            <div className="lp1-hero-content">
              <div className="lp1-hero-badge">AI That Actually Cares</div>
              <h1 className="lp1-hero-title">
                A teacher that actually<br />gives a damn.
              </h1>
              <p className="lp1-hero-desc">
                Remembers your struggles. Sees your work through your camera. Guides you without giving answers. Available 24/7 when you're actually studying.
              </p>
              <div className="lp1-hero-cta">
                <button onClick={onGetStarted} className="lp1-btn-primary">
                  Start Free Trial
                </button>
              </div>
              <p className="lp1-hero-sub">No credit card required</p>
            </div>

            {/* Floating Window Screenshot */}
            <div className="lp1-hero-screenshot">
              <img
                src="/landing-screenshots/floating_window_screenshot.png"
                alt="Floating window showing AI tutor helping with math problem"
                className="lp1-screenshot-img"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="lp1-features">
        <div className="lp1-container-narrow">
          <div className="lp1-section-title-box">
            <h2 className="lp1-section-title">What makes us different</h2>
          </div>
          <div className="lp1-features-grid">
            <div className="lp1-feature">
              <div className="lp1-feature-icon">
                <Brain size={28} strokeWidth={2} />
              </div>
              <h3>Remembers You</h3>
              <p>Tracks what you struggle with, what clicks, and adapts to your learning style over time.</p>
            </div>
            <div className="lp1-feature">
              <div className="lp1-feature-icon">
                <Eye size={28} strokeWidth={2} />
              </div>
              <h3>Sees Your Work</h3>
              <p>Show handwritten problems via camera. We spot exactly where you went wrong.</p>
            </div>
            <div className="lp1-feature">
              <div className="lp1-feature-icon">
                <Heart size={28} strokeWidth={2} />
              </div>
              <h3>Actually Cares</h3>
              <p>Knows when you're frustrated, when you need a break, and when you deserve encouragement.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="lp1-social">
        <div className="lp1-container">
          <div className="lp1-section-title-box lp1-section-title-box-pink">
            <h2 className="lp1-section-title">Testimonials</h2>
          </div>
          <div className="lp1-social-grid">
            <div className="lp1-testimonial">
              <div className="lp1-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#FFD93D" stroke="none" />)}
              </div>
              <p>"I used to fake sick to avoid math. Now I actually look forward to learning."</p>
              <span>Sarah M., 10th Grade</span>
            </div>
            <div className="lp1-testimonial">
              <div className="lp1-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#FFD93D" stroke="none" />)}
              </div>
              <p>"Better than $75/hr tutors. Available when he's doing homework at night."</p>
              <span>Parent of 8th Grader</span>
            </div>
            <div className="lp1-testimonial">
              <div className="lp1-stars">
                {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="#FFD93D" stroke="none" />)}
              </div>
              <p>"Remembered I wanted to be an engineer. Explained physics with engineering examples."</p>
              <span>Marcus T., 11th Grade</span>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="lp1-pricing">
        <div className="lp1-container">
          <div className="lp1-section-title-box lp1-section-title-box-violet">
            <h2 className="lp1-section-title">Elite tutoring.<br />Not elite prices.</h2>
          </div>

          <div className="lp1-pricing-grid">
            {/* Free Plan */}
            <div className="lp1-pricing-card">
              <div className="lp1-pricing-header">
                <h3 className="lp1-pricing-name">Free</h3>
                <div className="lp1-pricing-price">
                  <span className="lp1-price-amount">$0</span>
                  <span className="lp1-price-period">/month</span>
                </div>
                <p className="lp1-pricing-tagline">Try it out, no strings attached</p>
              </div>
              <ul className="lp1-pricing-features">
                <li><Check size={20} strokeWidth={3} />15 mins free everyday</li>
                <li><Check size={20} strokeWidth={3} />Basic question bank access</li>
                <li><Check size={20} strokeWidth={3} />Email support</li>
                <li><Check size={20} strokeWidth={3} />Progress tracking</li>
              </ul>
              <button onClick={onGetStarted} className="lp1-btn-pricing">
                Get Started
              </button>
            </div>

            {/* Starter Plan */}
            <div className="lp1-pricing-card">
              <div className="lp1-pricing-header">
                <h3 className="lp1-pricing-name">Starter</h3>
                <div className="lp1-pricing-price">
                  <span className="lp1-price-amount">$9.99</span>
                  <span className="lp1-price-period">/month</span>
                </div>
                <p className="lp1-pricing-tagline">Perfect for getting started</p>
              </div>
              <ul className="lp1-pricing-features">
                <li><Check size={20} strokeWidth={3} />10 hours of tutoring per month</li>
                <li><Check size={20} strokeWidth={3} />Basic question bank access</li>
                <li><Check size={20} strokeWidth={3} />Email support</li>
                <li><Check size={20} strokeWidth={3} />Progress tracking</li>
              </ul>
              <button onClick={onGetStarted} className="lp1-btn-pricing">
                Select Plan
              </button>
            </div>

            {/* Pro Plan */}
            <div className="lp1-pricing-card lp1-pricing-card-popular">
              <div className="lp1-popular-badge">
                <Star size={14} fill="#000000" stroke="none" />
                MOST POPULAR
              </div>
              <div className="lp1-pricing-header lp1-pricing-header-popular">
                <h3 className="lp1-pricing-name">Pro</h3>
                <div className="lp1-pricing-price">
                  <span className="lp1-price-amount">$19.99</span>
                  <span className="lp1-price-period">/month</span>
                </div>
                <p className="lp1-pricing-tagline">Most popular choice</p>
              </div>
              <ul className="lp1-pricing-features">
                <li><Check size={20} strokeWidth={3} />30 hours of tutoring per month</li>
                <li><Check size={20} strokeWidth={3} />Full question bank access</li>
                <li><Check size={20} strokeWidth={3} />Priority email support</li>
                <li><Check size={20} strokeWidth={3} />Advanced progress tracking</li>
                <li><Check size={20} strokeWidth={3} />Learning analytics</li>
                <li><Check size={20} strokeWidth={3} />Custom study plans</li>
              </ul>
              <button onClick={onGetStarted} className="lp1-btn-pricing lp1-btn-pricing-popular">
                Select Plan
              </button>
            </div>

            {/* Premium Plan */}
            <div className="lp1-pricing-card">
              <div className="lp1-pricing-header">
                <h3 className="lp1-pricing-name">Premium</h3>
                <div className="lp1-pricing-price">
                  <span className="lp1-price-amount">$39.99</span>
                  <span className="lp1-price-period">/month</span>
                </div>
                <p className="lp1-pricing-tagline">For serious learners</p>
              </div>
              <ul className="lp1-pricing-features">
                <li><Check size={20} strokeWidth={3} />Unlimited tutoring hours</li>
                <li><Check size={20} strokeWidth={3} />Full question bank access</li>
                <li><Check size={20} strokeWidth={3} />24/7 priority support</li>
                <li><Check size={20} strokeWidth={3} />Advanced progress tracking</li>
                <li><Check size={20} strokeWidth={3} />Detailed learning analytics</li>
                <li><Check size={20} strokeWidth={3} />Personalized study plans</li>
                <li><Check size={20} strokeWidth={3} />One-on-one sessions</li>
                <li><Check size={20} strokeWidth={3} />Early access to new features</li>
              </ul>
              <button onClick={onGetStarted} className="lp1-btn-pricing">
                Select Plan
              </button>
            </div>
          </div>

          <div className="lp1-pricing-footer">
            <p>All plans include a 7-day free trial. Cancel anytime.</p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="lp1-faq">
        <div className="lp1-container-narrow">
          <div className="lp1-section-title-box lp1-section-title-box-pink">
            <h2 className="lp1-section-title">Common questions</h2>
          </div>
          <div className="lp1-faq-list">
            {[
              {
                q: "Is this just ChatGPT for homework?",
                a: "No. ChatGPT gives you answers and forgets you exist. We guide you to figure it out yourself, remember everything about your learning journey, see your work through your camera, and build a real relationship over time."
              },
              {
                q: "Will it just do my homework for me?",
                a: "Nope. We guide you step-by-step and help you understand, but you're doing the work. That's how you actually learn."
              },
              {
                q: "What if I'm really behind in my class?",
                a: "Perfect. We meet you exactly where you are with zero judgment. Your pace is the right pace."
              },
              {
                q: "Is it available at 2 AM when I'm actually studying?",
                a: "Yes. We don't sleep, don't have office hours, and never get tired of helping."
              }
            ].map((faq, idx) => (
              <div key={idx} className="lp1-faq-item">
                <button
                  onClick={() => setOpenFAQ(openFAQ === idx ? null : idx)}
                  className="lp1-faq-question"
                >
                  <span>{faq.q}</span>
                  <ChevronDown
                    size={20}
                    className={`lp1-faq-icon ${openFAQ === idx ? 'open' : ''}`}
                  />
                </button>
                {openFAQ === idx && (
                  <div className="lp1-faq-answer">
                    <p>{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="lp1-final-cta">
        <div className="lp1-container-narrow">
          <div className="lp1-final-cta-box">
            <div className="lp1-section-title-box">
              <h2 className="lp1-section-title">Ready to start learning?</h2>
            </div>
            <button onClick={onGetStarted} className="lp1-btn-primary">
              Start Free Trial
            </button>
            <p className="lp1-final-sub">No credit card required</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="lp1-footer">
        <div className="lp1-container">
          <p>© 2025 Teachr.live</p>
          <div className="lp1-footer-links">
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage1;
