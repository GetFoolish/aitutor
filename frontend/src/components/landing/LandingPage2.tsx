/**
 * Landing Page Neo: Matching designprompts.dev Neo-Brutalism Reference
 * Content from landing-page-content_2.md
 * Visual style matching the reference screenshots
 */
import React, { useEffect, useState } from 'react';
import TeachrLogo from './TeachrLogo';
import './landing.scss';

interface LandingPageNeoProps {
  onGetStarted: () => void;
}

const LandingPageNeo: React.FC<LandingPageNeoProps> = ({ onGetStarted }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <div className="landing-page landing-page-neo-ref">
      {/* ===== HEADER ===== */}
      <header className="neo-ref-header">
        <div className="neo-ref-container">
          <div className="neo-ref-header-content">
            <div className="neo-ref-logo">
              <TeachrLogo size="large" />
            </div>
            <button onClick={onGetStarted} className="neo-ref-button neo-ref-button-primary">
              GET STARTED
            </button>
          </div>
        </div>
      </header>

      {/* ===== HERO SECTION with Halftone Background ===== */}
      <section className="neo-ref-hero">
        <div className="neo-ref-container">
          {/* Floating decorative shapes */}
          <div className="neo-ref-shape neo-ref-shape-red" style={{ top: '10%', left: '5%' }} />
          <div className="neo-ref-shape neo-ref-shape-yellow neo-ref-shape-circle" style={{ top: '15%', right: '8%' }} />
          
          <div className="neo-ref-hero-content">
            <h1 className="neo-ref-hero-title">
              <span className="neo-ref-title-line">WHAT IF YOU</span>
              <span className="neo-ref-title-line neo-ref-title-highlight">ACTUALLY UNDERSTOOD IT?</span>
            </h1>
            
            <div className="neo-ref-hero-description">
              <p className="neo-ref-text-large">
                Not memorized it for the test. Not faked your way through it. Actually got it. That's what we're building.
              </p>
              
              <div className="neo-ref-hero-cta">
                <button onClick={onGetStarted} className="neo-ref-button neo-ref-button-cta">
                  TRY IT FREE
                </button>
                <div className="neo-ref-badge neo-ref-badge-rotate">NO CREDIT CARD</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== THE REAL PROBLEM (White Section) ===== */}
      <section className="neo-ref-section neo-ref-section-white">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <div className="neo-ref-badge neo-ref-badge-small">THE PROBLEM</div>
            <h2 className="neo-ref-heading-xl">THE REAL PROBLEM</h2>
            <h3 className="neo-ref-heading-lg">You Don't Need More Content.<br />You Need Better Understanding.</h3>
          </div>

          <div className="neo-ref-card neo-ref-card-main">
            <p className="neo-ref-text-xl neo-ref-text-bold">
              The internet has more educational content than any human could consume in ten lifetimes.
            </p>
            <p className="neo-ref-text-md">
              Khan Academy. YouTube. Coursera. Udemy. Brilliant. That random guy with a whiteboard who pronounces "integral" weird.
            </p>
            <p className="neo-ref-text-xl neo-ref-text-emphasis">
              You're not struggling because there's not enough out there. You're struggling because none of it was built for you.
            </p>
            <p className="neo-ref-text-md">
              Generic explanations. One-size-fits-all pacing. Videos that assume you understood minute three when you got lost at minute one.
            </p>
            <p className="neo-ref-text-xl neo-ref-text-black">
              More content isn't the answer. Better teaching is.
            </p>
          </div>
        </div>
      </section>

      {/* ===== THE DIFFERENCE (Yellow Section with Grid) ===== */}
      <section className="neo-ref-section neo-ref-section-yellow">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <h2 className="neo-ref-heading-xl">THE DIFFERENCE</h2>
            <h3 className="neo-ref-heading-lg">Teaching vs. Content</h3>
          </div>

          <div className="neo-ref-comparison-wrapper">
            <div className="neo-ref-card neo-ref-card-rotate-left">
              <div className="neo-ref-badge neo-ref-badge-red neo-ref-badge-corner">CONTENT</div>
              <h4 className="neo-ref-card-title neo-ref-text-red">Content</h4>
              <ul className="neo-ref-list-simple">
                <li>is a video you pause, rewind, pause again, then give up on.</li>
                <li>moves at its own pace.</li>
                <li>doesn't know if you understood.</li>
              </ul>
            </div>

            <div className="neo-ref-card neo-ref-card-rotate-right">
              <div className="neo-ref-badge neo-ref-badge-yellow neo-ref-badge-corner">TEACHING</div>
              <h4 className="neo-ref-card-title">Teaching</h4>
              <ul className="neo-ref-list-simple">
                <li>is someone who notices you're confused and tries a different angle.</li>
                <li>moves at yours.</li>
                <li>checks. And adjusts. And checks again.</li>
              </ul>
            </div>
          </div>

          <p className="neo-ref-statement">
            teachr isn't content. It's teaching.
          </p>
        </div>
      </section>

      {/* ===== WHAT ACTUALLY CHANGES (Cream Section) ===== */}
      <section className="neo-ref-section neo-ref-section-cream">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <h2 className="neo-ref-heading-xl">WHAT ACTUALLY CHANGES</h2>
            <h3 className="neo-ref-heading-lg">When Learning Finally Works</h3>
          </div>

          <div className="neo-ref-grid neo-ref-grid-2">
            {[
              {
                title: "You stop avoiding the subject.",
                text: "That class you dread? The homework you leave until last? It's not because you're bad at it. It's because no one's taught you properly yet."
              },
              {
                title: "You build real confidence.",
                text: "Not the fake kind where you hope the test questions are easy. The kind where you walk in knowing you've got this."
              },
              {
                title: "You save time.",
                text: "No more watching 45-minute videos for 3 minutes of relevance. No more hunting through forums for someone who had your exact question. Just direct answers to what you actually need."
              },
              {
                title: "You start to like it.",
                text: "Controversial opinion: most subjects are interesting when you actually understand them. Math isn't boring. Bad teaching is boring."
              }
            ].map((item, idx) => (
              <div key={idx} className={`neo-ref-card ${idx % 2 === 0 ? 'neo-ref-card-rotate-left' : 'neo-ref-card-rotate-right'}`}>
                <h4 className="neo-ref-card-title">{item.title}</h4>
                <p className="neo-ref-text-md">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== HOW IT WORKS (Violet Section with Grid Pattern) ===== */}
      <section className="neo-ref-section neo-ref-section-violet">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <div className="neo-ref-badge neo-ref-badge-yellow">PROCESS</div>
            <h2 className="neo-ref-heading-xl">HOW IT WORKS</h2>
            <h3 className="neo-ref-heading-lg">Simple. Like It Should Be.</h3>
          </div>

          <div className="neo-ref-grid neo-ref-grid-3">
            {[
              {
                num: "1",
                title: "Bring Your Problem",
                text: 'A concept. A homework question. A "why does this even exist" rant. All valid starting points.'
              },
              {
                num: "2",
                title: "Learn Your Way",
                text: "Visual learner? We'll draw it out. Need real-world examples? Got those. Want the formal proof? Sure, weirdo, we have that too."
              },
              {
                num: "3",
                title: "Move On When You're Ready",
                text: "Not when the video ends. Not when the bell rings. When you actually get it."
              }
            ].map((step, idx) => (
              <div key={idx} className={`neo-ref-card neo-ref-card-step ${idx === 0 ? 'neo-ref-card-rotate-left' : idx === 2 ? 'neo-ref-card-rotate-right' : ''}`}>
                <div className="neo-ref-step-badge">{step.num}</div>
                <h4 className="neo-ref-card-title">{step.title}</h4>
                <p className="neo-ref-text-md">{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== CURRENTLY TEACHING (White Section) ===== */}
      <section className="neo-ref-section neo-ref-section-white">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <h2 className="neo-ref-heading-xl">CURRENTLY TEACHING</h2>
            <h3 className="neo-ref-heading-lg">Math. All of It.</h3>
          </div>

          <div className="neo-ref-content-narrow">
            <div className="neo-ref-card neo-ref-card-main">
              <ul className="neo-ref-list-bullets">
                <li><span className="neo-ref-bullet" />Arithmetic (no shame)</li>
                <li><span className="neo-ref-bullet" />Algebra</li>
                <li><span className="neo-ref-bullet" />Geometry</li>
                <li><span className="neo-ref-bullet" />Trigonometry</li>
                <li><span className="neo-ref-bullet" />Calculus</li>
                <li><span className="neo-ref-bullet" />Statistics</li>
                <li><span className="neo-ref-bullet" />Whatever hybrid monster your curriculum invented</li>
              </ul>
            </div>

            <div className="neo-ref-card neo-ref-card-yellow" style={{ marginTop: '32px' }}>
              <h4 className="neo-ref-card-title">Chemistry & Biology — Coming Soon</h4>
              <p className="neo-ref-text-md">
                We're building those out now. Want early access?{' '}
                <a href="#" onClick={(e) => { e.preventDefault(); onGetStarted(); }} className="neo-ref-link">
                  Get on the list.
                </a>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== THE HONEST TRUTH (Black Section) ===== */}
      <section className="neo-ref-section neo-ref-section-black">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <h2 className="neo-ref-heading-xl neo-ref-text-white">THE HONEST TRUTH</h2>
            <h3 className="neo-ref-heading-lg neo-ref-text-white">This Works If You Work</h3>
          </div>

          <div className="neo-ref-card neo-ref-card-white neo-ref-content-narrow">
            <p className="neo-ref-text-md">We're not selling magic. We're selling a better tool.</p>
            <p className="neo-ref-text-md">You still have to show up. You still have to try. You still have to do the practice problems.</p>
            <p className="neo-ref-text-md">But when you do? You'll actually understand them. Not just survive them.</p>
            <p className="neo-ref-text-xl neo-ref-text-emphasis">
              The difference between "I passed" and "I get it" is better teaching.
            </p>
            <p className="neo-ref-text-md">That's what we're here for.</p>
          </div>
        </div>
      </section>

      {/* ===== WHO GETS THE MOST OUT (Cream Section) ===== */}
      <section className="neo-ref-section neo-ref-section-cream">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <h2 className="neo-ref-heading-xl">WHO GETS THE MOST OUT OF THIS</h2>
            <h3 className="neo-ref-heading-lg">Be Honest. Is This You?</h3>
          </div>

          <div className="neo-ref-content-narrow">
            <div className="neo-ref-card neo-ref-card-main">
              <ul className="neo-ref-list-checks">
                <li><span className="neo-ref-check">✓</span>You've told yourself you're "just not a math person"</li>
                <li><span className="neo-ref-check">✓</span>You've watched the same concept explained 10 different ways and still don't get it</li>
                <li><span className="neo-ref-check">✓</span>You're tired of feeling behind</li>
                <li><span className="neo-ref-check">✓</span>You learn differently and regular classes don't work for you</li>
                <li><span className="neo-ref-check">✓</span>You want to actually understand, not just pass</li>
              </ul>
            </div>

            <p className="neo-ref-statement" style={{ marginTop: '48px' }}>
              If you nodded at any of those, we built this for you.
            </p>
          </div>
        </div>
      </section>

      {/* ===== WHAT WE'RE NOT (White Section) ===== */}
      <section className="neo-ref-section neo-ref-section-white">
        <div className="neo-ref-container">
          <div className="neo-ref-section-header">
            <h2 className="neo-ref-heading-xl">WHAT WE'RE NOT</h2>
            <h3 className="neo-ref-heading-lg">Clarity Is Kindness</h3>
          </div>

          <div className="neo-ref-grid neo-ref-grid-3">
            {[
              {
                title: "We're not a homework cheat code.",
                text: "If you want answers without understanding, go somewhere else. We're not interested."
              },
              {
                title: "We're not replacing your teachers.",
                text: "Good teachers are irreplaceable. We're the support system for when they're not available."
              },
              {
                title: "We're not a miracle.",
                text: "We're a tool. A really good one. But you still have to use it."
              }
            ].map((item, idx) => (
              <div key={idx} className={`neo-ref-card neo-ref-card-cream ${idx % 2 === 0 ? 'neo-ref-card-rotate-left' : 'neo-ref-card-rotate-right'}`}>
                <h4 className="neo-ref-card-title">{item.title}</h4>
                <p className="neo-ref-text-md">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== THE PITCH - FINAL CTA (Black Section with Coral Card) ===== */}
      <section className="neo-ref-section neo-ref-section-black">
        <div className="neo-ref-container">
          <div className="neo-ref-cta-box">
            <div className="neo-ref-badge neo-ref-badge-large neo-ref-badge-rotate">ONE SENTENCE</div>
            
            <h2 className="neo-ref-cta-title">THE PITCH</h2>
            <h3 className="neo-ref-cta-subtitle">One Sentence. No Tricks.</h3>
            
            <p className="neo-ref-cta-text">
              A personalized math tutor that's available 24/7, adapts to how you learn, and actually helps you understand.
            </p>
            
            <p className="neo-ref-cta-subtext">
              That's it. That's the product.
            </p>
            
            <button onClick={onGetStarted} className="neo-ref-button neo-ref-button-massive">
              START LEARNING NOW
            </button>
          </div>
        </div>
      </section>

      {/* ===== FOOTER (Yellow Section) ===== */}
      <footer className="neo-ref-footer">
        <div className="neo-ref-container">
          <div className="neo-ref-footer-content">
            <div className="neo-ref-footer-brand">
              <TeachrLogo size="large" />
              <p className="neo-ref-footer-tagline">Finally, teaching that teaches.</p>
            </div>
            
            <div className="neo-ref-footer-contact">
              <p>Questions?</p>
              <a href="mailto:contact@teachr.live" className="neo-ref-link-black">
                contact@teachr.live
              </a>
            </div>
          </div>
          
          <div className="neo-ref-footer-bottom">
            <p className="neo-ref-footer-quote">
              Because understanding beats memorizing. Every time.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPageNeo;
