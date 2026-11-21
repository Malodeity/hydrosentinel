# Putting HydroSentinel online (Render + Neon, free)

The database is **Neon** (already created and filled). The app is on **Render**. Render reads `render.yaml` in the repository and builds both parts.

## What is already done
- The Neon project exists, with the 169 authorities, 21 demo contractors, 60 demo reports and tickets already loaded.
- Strong logins were generated for the hosted demo and saved in the file `.env.neon` (not in git): `HOSTED_ADMIN_PASSWORD` for the admin and `HOSTED_DEMO_PASSWORD` for the contractors and the Ekurhuleni authority admin. **Open that file on your laptop to read them.**
- `render.yaml` describes both Render services. The app tolerates Neon going to sleep (`pool_pre_ping`).
- Proof: the full end-to-end check passed 27 of 27 against the Neon database, and the front end builds.

## What you do (about 15 minutes)
1. **Push the code.** The repo must contain `render.yaml` on GitHub: `git push origin main` (ask me first and I will do it with you).
2. Go to **render.com** and **sign up with GitHub**. Allow it to see the `Malodeity/hydrosentinel` repository.
3. In Render click **New +**, then **Blueprint**. Pick the repository. Render shows two services: `hydrosentinel-api` and `hydrosentinel`. Click **Apply**.
4. Render asks for the secret values of the API service. Enter them in the page, not anywhere else:
   - `DATABASE_URL`: the line starting `DATABASE_URL_UNPOOLED=` in `.env.neon` (copy only what is after the `=`, without the quotes).
   - `OPENAI_API_KEY`: your key (leave empty to use the AI fallbacks).
   - `ADMIN_PASSWORD`: the `HOSTED_ADMIN_PASSWORD` value.
   - `DEMO_CONTRACTOR_PASSWORD`: the `HOSTED_DEMO_PASSWORD` value.
5. Wait for both builds to finish (5 to 10 minutes). Render shows each service's web address.
6. **If the two addresses are not exactly** `https://hydrosentinel.onrender.com` and `https://hydrosentinel-api.onrender.com` (the names are taken by someone else), change two settings: on the API set `FRONTEND_URL` to the static site's real address, and on the static site set `VITE_API_URL` to the API's real address, then redeploy the static site.
7. Open the static site address. The first screen takes up to a minute while the API wakes up.

## Keep it awake (free)
Free services sleep after 15 minutes without a visit and take 30 to 60 seconds to wake. To avoid that for the moderator, create a free monitor at **uptimerobot.com** that opens `https://hydrosentinel-api.onrender.com/` every 5 minutes. Use `/`, not `/health`: `/` does not touch the database, so Neon can sleep.

## What to give the moderator
- The static site address.
- Admin: `admin@hydrosentinel.co.za` and `HOSTED_ADMIN_PASSWORD`.
- Contractor: `dlamini-pretorius@contractors.hydrosentinel.co.za` and `HOSTED_DEMO_PASSWORD`.
- A citizen needs no login: the Report Issue page.
- Tell them the first load can take a minute, photos uploaded on the hosted demo disappear when the service restarts, and the AI buttons are limited to 20 calls an hour.

## Limits to know
- Render's free service has 512 MB of memory. The risk model (XGBoost) fits, but I could not test that on Render itself.
- Free limits change. Check Render's and Neon's pages before relying on a month.
