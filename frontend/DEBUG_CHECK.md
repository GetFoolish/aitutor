# Debug Checklist for Blank Screen Issue

## Step 1: Check Browser Console for RED Errors

1. Open Browser DevTools (F12)
2. Go to Console tab
3. **Ignore yellow warnings** - those are harmless
4. Look for **RED error messages** starting with "Uncaught" or "Error"
5. Copy the full error message

Common errors to look for:
- `Uncaught ReferenceError`
- `Uncaught TypeError`
- `Failed to fetch`
- `Network request failed`

---

## Step 2: Check Network Tab

1. In DevTools, go to **Network** tab
2. Refresh the page (Cmd+R)
3. After logging in, check if these requests happen:
   - `GET http://localhost:8001/auth/me` (should return 200)
   - `GET http://localhost:8000/next-question/[user_id]` (should return 200 or 404)

If you see:
- **401 Unauthorized** - Authentication failed
- **404 Not Found** - No questions available (this is OK for first time)
- **500 Internal Server Error** - Backend crashed
- **Failed to fetch** - Backend not running

---

## Step 3: Check Elements Tab

1. In DevTools, go to **Elements** tab
2. Look at the HTML structure
3. Find `<div id="root">`
4. Check if there's anything inside it

If you see:
- Empty `<div id="root"></div>` - React isn't mounting
- Lots of nested divs - React is rendering but CSS might be hiding it

---

## Step 4: Quick Test Commands

Run these in your browser console:

```javascript
// Check if user is logged in
localStorage.getItem('token')

// Check if user object exists
localStorage.getItem('user')
```

Should show:
- Token: A long JWT string starting with "eyJ"
- User: A JSON object with your email

---

## Step 5: Check CSS Display Issues

In browser console, run:
```javascript
document.body.style.opacity = "1"
document.body.style.visibility = "visible"
document.getElementById('root').style.display = "block"
```

Does anything appear?
- **Yes** - It's a CSS issue
- **No** - It's a JavaScript/React render issue

---

## Common Fixes

### Fix 1: Clear Everything and Restart
```bash
# Clear browser storage
localStorage.clear()
sessionStorage.clear()

# Then refresh page and login again
```

### Fix 2: Check if logged in but API failing
If you're logged in but see blank screen, the issue is likely:
1. DASH API not returning questions
2. Component crashing on render
3. Network request timing out

---

## Report Back

Please share:
1. Any RED errors from Console tab
2. Status of Network requests (especially /auth/me and /next-question)
3. What's in localStorage for 'token' and 'user'
4. What you see in Elements tab under `<div id="root">`
