<!-- LOVABLE:BEGIN -->

> [!IMPORTANT]
> This project is connected to Lovable. Avoid rewriting published git history.

<!-- LOVABLE:END -->

- Keep enquiry fixtures in `src/data` and chat state orchestration in `src/hooks/useChat.ts` so a future API can replace mocks without rewriting presentation components.
- Keep shared navigation and theme behavior in `SiteShell` so all public routes remain visually consistent.
