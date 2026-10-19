
const API_BASE = "http://127.0.0.1:8000";

const loginForm = document.getElementById("login-form");
const loginButton = document.getElementById("login-button");
const loginMessage = document.getElementById("login-message");

loginForm.addEventListener("submit", async function (event) {
    // Prevent the browser from reloading the page
    event.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    loginButton.disabled = true;
    loginButton.textContent = "Signing in...";
    loginMessage.textContent = "";
    loginMessage.className = "message";

    try {
        // Step 1: Send login details to FastAPI
        const loginResponse = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const loginData = await loginResponse.json();

        if (!loginResponse.ok) {
            throw new Error(
                loginData.detail || "Login failed. Check your credentials."
            );
        }

        // Step 2: Save the tokens for this browser session
        sessionStorage.setItem("access_token", loginData.access_token);
        sessionStorage.setItem("refresh_token", loginData.refresh_token);

        // Step 3: Ask the backend who logged in
        const profileResponse = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                "Authorization": `Bearer ${loginData.access_token}`
            }
        });

        const profileData = await profileResponse.json();

        if (!profileResponse.ok) {
            throw new Error(
                profileData.detail || "Could not load your profile."
            );
        }

        // Step 4: Display the login result
        loginMessage.className = "message success";
        loginMessage.textContent =
            `Login successful! Welcome, ${profileData.username}. Role: ${profileData.role}`;

        console.log("Logged-in user:", profileData);

    } catch (error) {
        loginMessage.className = "message error";
        loginMessage.textContent =
            error.message === "Failed to fetch"
                ? "Cannot connect to the backend. Check that FastAPI is running and CORS is configured."
                : error.message;

        // Clear tokens if login or profile loading failed
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("refresh_token");

    } finally {
        loginButton.disabled = false;
        loginButton.textContent = "Sign In";
    }
});
