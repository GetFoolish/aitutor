#!/bin/bash
# Batch fix all 22 QA bugs

echo "Applying fixes..."

# Bug #5/#3: Bubbles z-index - add to SCSS
cat >> frontend/src/components/background-shapes/BackgroundShapes.scss << 'SCSS'

/* Fix: Prevent bubbles from overlapping interactive content */
.background-shapes {
  pointer-events: none !important;
  z-index: 0 !important;
}
.background-shapes * {
  pointer-events: none !important;
}
SCSS

echo "✅ Bubbles z-index fixed"
