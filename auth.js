const jwt = require('jsonwebtoken');
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
