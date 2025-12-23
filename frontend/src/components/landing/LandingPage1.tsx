/**
 * Landing Page 1: Neo-Brutalism Style
 * Matches the existing system design - Enhanced with more details
 */
import React from 'react';
import TeachrLogo from './TeachrLogo';


interface LandingPage1Props {
  onGetStarted: () => void;
}

const LandingPage1: React.FC<LandingPage1Props> = ({ onGetStarted }) => {
  return (
    <div className="landing-page landing-page-1">
      <div className="landing-container">
        {/* Header */}
        <header className="landing-header">
          <TeachrLogo size="medium" />
          <nav className="flex gap-4 md:gap-6 items-center hidden sm:flex">
            <a href="#features" className="text-black no-underline font-bold text-sm uppercase">Features</a>
            <a href="#how-it-works" className="text-black no-underline font-bold text-sm uppercase">How It Works</a>
          </nav>
        </header>

        {/* Hero Section */}
        <section className="landing-hero">
          <div className="hero-content">
            <div className="inline-block px-5 py-2 bg-[#FFD93D] border-4 border-black mb-6 text-xs font-black uppercase tracking-widest">
              AI-Powered Learning Platform
            </div>
            <h1 className="hero-title">
              Learn Smarter, Not Harder
            </h1>
            <p className="hero-subtitle">
              Teachr adapts to your learning style, providing personalized practice questions that match your skill level. Get real-time help from our AI tutor, track your progress, and master any subject at your own pace.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-8">
              <button
                onClick={onGetStarted}
                className="cta-button cta-button-neo w-full sm:w-auto"
              >
                Start Learning Free
              </button>
              <button
                onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-8 py-4 text-lg font-bold bg-transparent text-black border-4 border-black uppercase tracking-wider cursor-pointer transition-all duration-100 ease-out hover:bg-black hover:text-white w-full sm:w-auto"
              >
                Learn More
              </button>
            </div>
          </div>
          <div className="hero-image hidden md:block">
            <img
              src="/landing-screenshots/home-screen-placeholder.png"
              alt="Teachr Learning Interface"
              className="w-full h-auto border-4 border-black shadow-[12px_12px_0_0_#000] rounded-none"
            />
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how-it-works" className="py-16 md:py-24 bg-white">
          <h2 className="text-4xl md:text-[56px] font-black text-center mb-4 uppercase tracking-tighter">
            How It Works
          </h2>
          <p className="text-lg md:text-xl font-bold text-center mb-10 md:mb-16 text-black">
            Three simple steps to start your learning journey
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-10 mt-10 md:mt-16">
            {[
              {
                number: '01',
                title: 'Sign Up & Set Your Grade',
                description: 'Create your account with Google and tell us your grade level. Our system automatically personalizes content for your age and learning stage.'
              },
              {
                number: '02',
                title: 'Practice with Adaptive Questions',
                description: 'Start practicing with questions that adapt to your skill level. Our AI analyzes your performance and adjusts difficulty in real-time.'
              },
              {
                number: '03',
                title: 'Get Help & Track Progress',
                description: 'Stuck on a problem? Ask our AI tutor for instant help. Watch your skills improve with detailed progress tracking for every topic.'
              }
            ].map((step, idx) => (
              <div
                key={idx}
                className="bg-white border-4 border-black p-8 md:p-10 shadow-[8px_8px_0_0_#000] relative"
              >
                <div
                  className="text-6xl md:text-[72px] font-black text-[#FFD93D] leading-none mb-5"
                  style={{
                    WebkitTextStroke: '4px #000000',
                  }}
                >
                  {step.number}
                </div>
                <h3
                  className="text-2xl font-black mb-4 uppercase tracking-wider"
                  style={{
                    WebkitTextStroke: "1px black",
                  }}
                >
                  {step.title}
                </h3>
                <p className="text-base font-bold leading-relaxed text-black">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="landing-features">
          <div className="text-center mb-10 md:mb-16">
            <h2 className="text-4xl md:text-[56px] font-black mb-4 uppercase tracking-tighter">
              Powerful Features
            </h2>
            <p className="text-lg md:text-xl font-bold text-black">
              Everything you need to succeed in your learning journey
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
            <div className="feature-card">
              <div className="feature-icon">🎯</div>
              <h3>Adaptive Learning System</h3>
              <p>Our intelligent system analyzes your performance and automatically adjusts question difficulty. Questions get harder as you improve and easier when you need more practice. No two students see the same learning path.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>AI-Powered Real-Time Tutoring</h3>
              <p>Get instant help from our AI tutor powered by Google Gemini. Ask questions via voice or text, receive step-by-step explanations, and get personalized guidance whenever you're stuck. Available 24/7.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Comprehensive Progress Tracking</h3>
              <p>Track your improvement with detailed analytics. See memory strength for each skill, practice counts, accuracy rates, and identify areas that need more attention. Visualize your learning journey.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">✨</div>
              <h3>Interactive Question Types</h3>
              <p>Engage with diverse question formats including multiple choice, numeric input, graphing exercises, drag-and-drop, and more. Rich, interactive content makes learning engaging and effective.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🎓</div>
              <h3>Grade-Appropriate Content</h3>
              <p>Content automatically matches your grade level from Kindergarten through 12th grade. The system ensures you're always practicing at the right level for your age and learning stage.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3>Instant Feedback & Corrections</h3>
              <p>Get immediate feedback on every answer. Learn from mistakes with detailed explanations and understand concepts better through real-time corrections and hints.</p>
            </div>
          </div>
        </section>

        {/* Benefits Section */}
        <section className="py-16 md:py-24 bg-[#FFD93D] border-4 border-black my-10 md:my-16 shadow-[8px_8px_0_0_#000] md:shadow-[12px_12px_0_0_#000]">
          <h2 className="text-3xl md:text-5xl font-black text-center mb-10 uppercase tracking-tighter px-4">
            Why Students Love Teachr
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 max-w-[1000px] mx-auto px-6">
            {[
              'Practice at your own pace - no pressure, no deadlines',
              'Questions adapt to your skill level automatically',
              'Get help instantly from AI tutor when stuck',
              'Track progress and see improvement over time',
              'Learn from mistakes with detailed explanations',
              'Engaging interactive questions keep you motivated'
            ].map((benefit, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 p-5 bg-white border-4 border-black shadow-[4px_4px_0_0_#000]"
              >
                <div className="w-6 h-6 bg-black shrink-0" />
                <p className="text-base md:text-lg font-bold m-0 text-black">
                  {benefit}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section className="landing-cta">
          <h2>Ready to Transform Your Learning?</h2>
          <p>Join thousands of students who are mastering new skills and building confidence every day with Teachr.</p>
          <button
            onClick={onGetStarted}
            className="cta-button cta-button-neo cta-button-large w-full md:w-auto"
          >
            Get Started Now
          </button>
          <p className="text-sm font-bold mt-6 text-black opacity-70">
            Free to start • No credit card required • Cancel anytime
          </p>
        </section>

        {/* Footer */}
        <footer className="landing-footer">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="m-0 text-center md:text-left">© 2024 Teachr. Making learning accessible for everyone.</p>
            <div className="flex gap-6">
              <a href="#" className="text-black no-underline font-bold text-sm">Privacy</a>
              <a href="#" className="text-black no-underline font-bold text-sm">Terms</a>
              <a href="#" className="text-black no-underline font-bold text-sm">Contact</a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default LandingPage1;

