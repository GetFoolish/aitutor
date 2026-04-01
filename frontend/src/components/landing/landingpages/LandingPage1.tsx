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
                <button
                  onClick={() => window.location.href = '/app/dev-login'}
                  className="lp1-btn-primary"
                  style={{ background: '#FF6B6B', color: '#fff', fontSize: '18px', padding: '14px 28px' }}
                >
                  Try It Free →
                </button>
              </div>
              <p className="lp1-hero-sub">No credit card required</p>
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginTop: '8px' }}>
            <div style={{ padding: '24px', border: '4px solid #000', background: '#FFD93D', boxShadow: '4px 4px 0 #000' }}>
              <div style={{ fontSize: '24px', marginBottom: '12px' }}>🤖</div>
              <h3 style={{ fontSize: '16px', fontWeight: 900, textTransform: 'uppercase', marginBottom: '8px', margin: '0 0 8px 0' }}>AI Questions</h3>
              <p style={{ fontSize: '14px', color: '#333', lineHeight: 1.5, margin: 0 }}>Gemini AI generates unique questions for your exact level</p>
            </div>
            <div style={{ padding: '24px', border: '4px solid #000', background: '#FFD93D', boxShadow: '4px 4px 0 #000' }}>
              <div style={{ fontSize: '24px', marginBottom: '12px' }}>📚</div>
              <h3 style={{ fontSize: '16px', fontWeight: 900, textTransform: 'uppercase', marginBottom: '8px', margin: '0 0 8px 0' }}>Any Subject</h3>
              <p style={{ fontSize: '14px', color: '#333', lineHeight: 1.5, margin: 0 }}>Math, Science, English, History — or type your own</p>
            </div>
            <div style={{ padding: '24px', border: '4px solid #000', background: '#FFD93D', boxShadow: '4px 4px 0 #000' }}>
              <div style={{ fontSize: '24px', marginBottom: '12px' }}>⚡</div>
              <h3 style={{ fontSize: '16px', fontWeight: 900, textTransform: 'uppercase', marginBottom: '8px', margin: '0 0 8px 0' }}>Instant Results</h3>
              <p style={{ fontSize: '14px', color: '#333', lineHeight: 1.5, margin: 0 }}>10 questions, grade-level score, done in minutes</p>
            </div>
          </div>
          <div style={{ textAlign: 'center', marginTop: '32px' }}>
            <button
              onClick={() => window.location.href = '/app/dev-login'}
              style={{ background: '#FF4B4B', color: 'white', border: '2px solid #000', boxShadow: '4px 4px 0 #000', padding: '16px 32px', fontWeight: 700, fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.05em', cursor: 'pointer' }}
            >
              START LEARNING FREE →
            </button>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section style={{ padding: '40px 20px', background: '#FFD93D', borderTop: '4px solid #000', borderBottom: '4px solid #000' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexWrap: 'wrap' as const, gap: '16px', justifyContent: 'center' }}>
          {[
            { number: '10,000+', label: 'Students' },
            { number: '4.9★', label: 'Average Rating' },
            { number: '95%', label: 'Say It Helped' },
          ].map((stat, i) => (
            <div key={i} style={{
              border: '4px solid #000',
              background: '#fff',
              padding: '20px 32px',
              boxShadow: '4px 4px 0 #000',
              textAlign: 'center',
              minWidth: '160px',
            }}>
              <div style={{ fontSize: '32px', fontWeight: 900, letterSpacing: '-0.02em' }}>{stat.number}</div>
              <div style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#666', marginTop: '4px' }}>{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
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

      {/* Privacy Section */}
      <section style={{ padding: '60px 20px', background: '#fff', borderTop: '4px solid #000' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <h2 style={{
            fontSize: '28px',
            fontWeight: 900,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '8px',
            textAlign: 'center',
          }}>
            Built for Parents Too
          </h2>
          <p style={{ textAlign: 'center', color: '#666', marginBottom: '32px', fontSize: '16px' }}>
            We take your child's privacy seriously.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            {[
              { icon: '🎥', text: 'Camera processed locally — never stored, never shared' },
              { icon: '🛡️', text: 'COPPA compliant — safe for students under 13' },
              { icon: '🔑', text: 'You control the data — delete anytime' },
              { icon: '🚫', text: 'No ads, no selling data, ever' },
            ].map((item, i) => (
              <div key={i} style={{
                border: '4px solid #000',
                background: '#FFFDF5',
                padding: '20px',
                boxShadow: '4px 4px 0 #000',
                display: 'flex',
                gap: '12px',
                alignItems: 'flex-start',
              }}>
                <span style={{ fontSize: '24px', flexShrink: 0 }}>{item.icon}</span>
                <span style={{ fontSize: '15px', fontWeight: 700, lineHeight: 1.4 }}>{item.text}</span>
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

      <style>{`
        .lp1-header {
          padding: 16px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 4px solid #000;
          background: #FFFDF5;
        }
        .lp1-container,
        .lp1-container-narrow {
          max-width: 960px;
          margin: 0 auto;
          padding: 0 24px;
        }
        .lp1-nav {
          display: flex;
          align-items: center;
          gap: 24px;
        }
        .lp1-nav a {
          font-weight: 700;
          text-decoration: none;
          color: #000;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .lp1-btn-header,
        .lp1-btn-primary {
          padding: 10px 20px;
          border: 4px solid #000;
          background: #FFD93D;
          font-weight: 900;
          text-transform: uppercase;
          cursor: pointer;
          box-shadow: 4px 4px 0 #000;
          letter-spacing: 0.05em;
        }
        .lp1-hero {
          padding: 60px 0;
          text-align: center;
        }
        .lp1-hero-badge {
          display: inline-block;
          padding: 6px 16px;
          border: 4px solid #000;
          background: #FF6B6B;
          color: #fff;
          font-weight: 900;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-bottom: 20px;
          box-shadow: 4px 4px 0 #000;
        }
        .lp1-hero-title {
          font-size: 48px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: -0.02em;
          margin-bottom: 16px;
          line-height: 1.1;
        }
        .lp1-hero-desc {
          font-size: 18px;
          font-weight: 600;
          color: #555;
          margin-bottom: 28px;
          max-width: 600px;
          margin-left: auto;
          margin-right: auto;
          line-height: 1.6;
        }
        .lp1-hero-cta {
          margin-bottom: 12px;
        }
        .lp1-hero-sub {
          font-size: 13px;
          color: #888;
          font-weight: 600;
        }
        .lp1-features,
        .lp1-social,
        .lp1-pricing {
          padding: 60px 0;
        }
        .lp1-section-title-box {
          text-align: center;
          margin-bottom: 40px;
        }
        .lp1-section-title {
          font-size: 32px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: -0.02em;
        }
        .lp1-features-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        @media (max-width: 768px) {
          .lp1-features-grid {
            grid-template-columns: 1fr;
          }
        }
        .lp1-feature {
          padding: 24px;
          border: 4px solid #000;
          background: #fff;
          box-shadow: 4px 4px 0 #000;
        }
        .lp1-feature-icon {
          width: 48px;
          height: 48px;
          border: 4px solid #000;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #FFD93D;
          margin-bottom: 16px;
          box-shadow: 4px 4px 0 #000;
        }
        .lp1-feature h3 {
          font-size: 18px;
          font-weight: 900;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .lp1-feature p {
          font-size: 14px;
          font-weight: 600;
          color: #444;
          line-height: 1.5;
        }
        .lp1-social-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        @media (max-width: 768px) {
          .lp1-social-grid {
            grid-template-columns: 1fr;
          }
        }
        .lp1-testimonial {
          padding: 24px;
          border: 4px solid #000;
          background: #fff;
          box-shadow: 4px 4px 0 #000;
        }
        .lp1-testimonial p {
          font-size: 15px;
          font-weight: 600;
          color: #333;
          margin: 12px 0;
          line-height: 1.5;
          font-style: italic;
        }
        .lp1-testimonial span {
          font-size: 13px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .lp1-stars {
          display: flex;
          gap: 4px;
          margin-bottom: 8px;
        }
        .lp1-pricing-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        @media (max-width: 768px) {
          .lp1-pricing-grid {
            grid-template-columns: 1fr;
          }
        }
        .lp1-pricing-card {
          padding: 28px;
          border: 4px solid #000;
          background: #fff;
          box-shadow: 4px 4px 0 #000;
          position: relative;
        }
        .lp1-pricing-card-popular {
          background: #FFD93D !important;
          transform: scale(1.02);
          box-shadow: 8px 8px 0 #000 !important;
        }
        .lp1-pricing-name {
          font-size: 20px;
          font-weight: 900;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .lp1-pricing-price {
          display: flex;
          align-items: baseline;
          gap: 4px;
          margin-bottom: 8px;
        }
        .lp1-price-amount {
          font-size: 36px;
          font-weight: 900;
        }
        .lp1-price-period {
          font-size: 14px;
          font-weight: 700;
          color: #666;
        }
        .lp1-pricing-tagline {
          font-size: 13px;
          font-weight: 600;
          color: #666;
          margin-bottom: 16px;
        }
        .lp1-pricing-features {
          list-style: none;
          padding: 0;
          margin: 0 0 20px 0;
        }
        .lp1-pricing-features li {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          padding: 6px 0;
          border-bottom: 2px solid #000;
        }
        .lp1-btn-pricing {
          width: 100%;
          padding: 12px 20px;
          border: 4px solid #000;
          background: #000;
          color: #fff;
          font-weight: 900;
          text-transform: uppercase;
          cursor: pointer;
          box-shadow: 4px 4px 0 #555;
          letter-spacing: 0.05em;
        }
        .lp1-popular-badge {
          position: absolute;
          top: -14px;
          right: 16px;
          background: #FF6B6B;
          color: #fff;
          padding: 4px 12px;
          font-size: 11px;
          font-weight: 900;
          text-transform: uppercase;
          border: 3px solid #000;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .lp1-faq {
          padding: 60px 0 80px;
        }
        .lp1-faq-item {
          border: 4px solid #000;
          margin-bottom: 8px;
          box-shadow: 4px 4px 0 #000;
          overflow: hidden;
        }
        .lp1-faq-question {
          padding: 16px 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
          font-weight: 900;
          font-size: 16px;
          text-transform: uppercase;
          background: #fff;
          width: 100%;
          border: none;
        }
        .lp1-faq-answer {
          padding: 16px 20px;
          border-top: 4px solid #000;
          background: #FFFDF5;
          font-size: 14px;
          font-weight: 600;
          line-height: 1.6;
          color: #444;
        }
        .lp1-footer {
          text-align: center;
          padding: 40px 24px;
          border-top: 4px solid #000;
          font-size: 13px;
          font-weight: 700;
        }
      `}</style>
    </div>
  );
};

export default LandingPage1;
