// Run this in browser console to debug assessment flow
(async function() {
  console.log('=== DEBUGGING ASSESSMENT FLOW ===');

  // 1. Check if we're authenticated
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  console.log('1. Auth token exists:', !!token);
  if (token) {
    console.log('   Token preview:', token.substring(0, 50) + '...');
  }

  // 2. Check session storage
  const subject = sessionStorage.getItem('selected_subject');
  const onboarding = sessionStorage.getItem('onboarding_complete');
  console.log('2. Selected subject:', subject);
  console.log('3. Onboarding complete:', onboarding);

  // 3. Try to start assessment
  if (!token) {
    console.error('4. Cannot test - no auth token. Go through dev-login first!');
    return;
  }

  console.log('4. Testing assessment start API...');
  try {
    const response = await fetch('http://localhost:8000/assessment/start-adaptive/Science', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({})
    });

    console.log('   Response status:', response.status);
    const data = await response.json();
    console.log('   Response data:', data);

    if (response.ok) {
      console.log('✅ Assessment API works! Question loaded:', data.question?.question?.content?.substring(0, 100));
    } else {
      console.error('❌ Assessment API failed:', data);
    }
  } catch (err) {
    console.error('❌ Network error:', err);
  }

  // 4. Check for JavaScript errors
  console.log('5. Checking for React errors...');
  const reactErrors = window.__REACT_ERROR_OVERLAY_GLOBAL_HOOK__?.errors || [];
  console.log('   React errors:', reactErrors.length);

  console.log('=== DEBUG COMPLETE ===');
})();
