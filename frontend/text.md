## 📋 SPECIFIC FILE-LEVEL ISSUES

### FloatingControlPanel.tsx
-  **Reduce component complexity** - 1328 lines is too large
  - Split into: ControlButtons, MediaControls, SessionTimer, etc.
-  **Remove duplicate state** and unused variables
-  **Extract business logic** to custom hooks
-  **Add prop types validation** with PropTypes or Zod

### App.tsx
-  **Remove unused imports** (commented out useLiveAPIContext)
-  **Simplify media mixer initialization** - too complex in main app
-  **Extract media handling** to a custom hook or context

### Header.tsx
-  **Implement actual user data** from AuthContext
-  **Add functional logout** handler
-  **Make dark mode toggle work** or remove commented code
-  **Add notifications icon** for future use

### GoogleSignIn.tsx
-  **Remove dev mode test button** from production builds
-  **Add proper error handling** for OAuth failures
-  **Implement retry logic** for failed requests

### QuestionDisplay.tsx
-  **Add error boundary** for widget rendering failures
-  **Implement question preloading** for better performance
-  **Add analytics tracking** for question interactions

### Styling Files
-  **Consolidate CSS files** - too many scattered style definitions
  - App.scss
  - index.css
  - mobile-fixes.css
  - ai-chat-improvements.css
  - Multiple component-specific SCSS files
-  **Use CSS-in-JS or Tailwind consistently** - current mix is confusing
-  **Remove duplicate style definitions**

---

## 🎯 ADDITIONAL RECOMMENDATIONS

### Code Organization
1. **Create a `constants` folder** for magic numbers and strings
2. **Add a `types` folder** with shared TypeScript interfaces
3. **Organize hooks** by category (data-fetching, UI, media, etc.)
4. **Create a `utils` folder** with pure utility functions
5. **Add a `config` folder** for app-wide configuration

### Best Practices
1. **Follow React 18 patterns** - use concurrent features where beneficial
2. **Implement proper TypeScript** - reduce `any` types (found in multiple places)
3. **Add proper error boundaries** around async components
4. **Use semantic HTML** for better SEO and accessibility
5. **Implement proper loading strategies** for heavy dependencies

### Third-Party Dependencies
1. **Audit package.json** for:
   - Unused dependencies (jquery ^1.11.3 is ancient!)
   - Security vulnerabilities
   - Bundle size impact
2. **Update deprecated packages**
3. **Consider alternatives** to heavy dependencies

### Performance Metrics
1. **Set up Lighthouse CI** (already configured but verify it runs)
2. **Monitor Core Web Vitals**
3. **Add performance budgets**
4. **Implement lazy loading** for routes and components
5. **Optimize font loading** (Space Mono, Space Grotesk)