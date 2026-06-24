import requests
import json
import base64

# ============================================================
# FILL THESE IN BEFORE RUNNING
# ============================================================
GITHUB_TOKEN = "ghp_your_token_here"   # your GitHub personal access token
OWNER        = "your_github_username"  # e.g. "Subhitcha04"
REPO         = "code-review-demo"      # repo name you will create
# ============================================================

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json"
}

BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"

# ─────────────────────────────────────────────
# STEP 1 — Create the repository
# ─────────────────────────────────────────────
def create_repo():
    print("📦 Creating repository...")
    url = "https://api.github.com/user/repos"
    payload = {
        "name": REPO,
        "description": "Demo repo for Code Review Agent",
        "private": False,
        "auto_init": True  # creates main branch with README
    }
    res = requests.post(url, headers=HEADERS, json=payload)
    if res.status_code == 201:
        print(f"✅ Repo created: https://github.com/{OWNER}/{REPO}")
    elif res.status_code == 422:
        print(f"⚠️  Repo already exists — continuing...")
    else:
        print(f"❌ Error creating repo: {res.json()}")
        exit(1)

# ─────────────────────────────────────────────
# STEP 2 — Get the SHA of main branch
# ─────────────────────────────────────────────
def get_main_sha():
    print("🔍 Getting main branch SHA...")
    res = requests.get(f"{BASE_URL}/git/ref/heads/main", headers=HEADERS)
    sha = res.json()["object"]["sha"]
    print(f"✅ Main SHA: {sha[:8]}...")
    return sha

# ─────────────────────────────────────────────
# STEP 3 — Create a new branch
# ─────────────────────────────────────────────
def create_branch(main_sha):
    print("🌿 Creating branch feature/auth...")
    payload = {
        "ref": "refs/heads/feature/auth",
        "sha": main_sha
    }
    res = requests.post(f"{BASE_URL}/git/refs", headers=HEADERS, json=payload)
    if res.status_code == 201:
        print("✅ Branch feature/auth created")
    elif res.status_code == 422:
        print("⚠️  Branch already exists — continuing...")
    else:
        print(f"❌ Error: {res.json()}")

# ─────────────────────────────────────────────
# STEP 4 — Push the bad auth code as a file
# ─────────────────────────────────────────────
def push_bad_code():
    print("📝 Pushing vulnerable auth code...")

    # This is the intentionally bad code the agent will review
    bad_code = '''const jwt = require('jsonwebtoken');
const express = require('express');
const app = express();
app.use(express.json());

// BAD: Hardcoded secret
const SECRET = "hardcoded_secret_123";

// BAD: SQL Injection + plain text password + no try-catch
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    const user = await db.query(
        "SELECT * FROM users WHERE username = '" + username + "'"
    );
    if (user && password === user.password) {
        const token = jwt.sign({ id: user.id }, SECRET);
        res.json({ token });
    } else {
        res.status(401).send('Unauthorized');
    }
});

// BAD: No token check, no try-catch, wrong header
app.get('/profile', (req, res) => {
    const token = req.headers.token;
    const decoded = jwt.verify(token, SECRET);
    res.json(decoded);
});

app.listen(3000);
'''

    # Get current file SHA if exists (needed for update)
    file_sha = None
    check = requests.get(f"{BASE_URL}/contents/auth.js?ref=feature/auth", headers=HEADERS)
    if check.status_code == 200:
        file_sha = check.json()["sha"]

    # Encode content to base64
    content_b64 = base64.b64encode(bad_code.encode()).decode()

    payload = {
        "message": "Add user authentication endpoint",
        "content": content_b64,
        "branch": "feature/auth"
    }
    if file_sha:
        payload["sha"] = file_sha

    res = requests.put(f"{BASE_URL}/contents/auth.js", headers=HEADERS, json=payload)
    if res.status_code in [200, 201]:
        print("✅ auth.js pushed to feature/auth branch")
    else:
        print(f"❌ Error pushing file: {res.json()}")
        exit(1)

# ─────────────────────────────────────────────
# STEP 5 — Create the Pull Request
# ─────────────────────────────────────────────
def create_pull_request():
    print("🔀 Creating Pull Request...")
    payload = {
        "title": "Add user authentication endpoint",
        "body": "This PR adds a login and profile endpoint using JWT authentication.",
        "head": "feature/auth",
        "base": "main"
    }
    res = requests.post(f"{BASE_URL}/pulls", headers=HEADERS, json=payload)
    if res.status_code == 201:
        pr = res.json()
        print(f"\n🎉 Pull Request created successfully!")
        print(f"   PR Number : {pr['number']}")
        print(f"   PR Title  : {pr['title']}")
        print(f"   PR URL    : {pr['html_url']}")
        print(f"\n📋 Use this PR number in your Flowise tool: {pr['number']}")
        return pr['number']
    elif res.status_code == 422:
        # PR already exists — fetch it
        res2 = requests.get(f"{BASE_URL}/pulls?head={OWNER}:feature/auth&state=open", headers=HEADERS)
        prs = res2.json()
        if prs:
            pr = prs[0]
            print(f"⚠️  PR already exists:")
            print(f"   PR Number : {pr['number']}")
            print(f"   PR URL    : {pr['html_url']}")
            return pr['number']
    else:
        print(f"❌ Error creating PR: {res.json()}")
        return None

# ─────────────────────────────────────────────
# STEP 6 — Print what to update in Flowise
# ─────────────────────────────────────────────
def print_flowise_instructions(pr_number):
    print("\n" + "="*50)
    print("📌 NOW UPDATE YOUR FLOWISE TOOLS:")
    print("="*50)
    print(f"""
In prfetchertool function, update these 4 lines at the top:

const GITHUB_TOKEN = '{GITHUB_TOKEN}';
const OWNER        = '{OWNER}';
const REPO         = '{REPO}';
const PR_NUMBER    = {pr_number};

In postcomment function, update the same 4 lines.

Then save and test with: Review PR #{pr_number}
""")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🚀 Setting up Code Review Agent Demo\n" + "="*40)

    if GITHUB_TOKEN == "ghp_your_token_here":
        print("❌ Please fill in your GITHUB_TOKEN, OWNER, and REPO before running!")
        exit(1)

    create_repo()
    main_sha = get_main_sha()
    create_branch(main_sha)
    push_bad_code()
    pr_number = create_pull_request()
    if pr_number:
        print_flowise_instructions(pr_number)
