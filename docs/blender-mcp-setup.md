# Blender MCP setup

Connects Claude Code to a running Blender instance so it can inspect and build
scenes directly.

Package: [`mcp-for-blender`](https://github.com/ahujasid/blender-mcp)
(renamed from `blender-mcp`). Requires Blender 3.0 or newer.

## Why this only works locally

The MCP server talks to a socket the Blender addon opens on `localhost:9876`.
That means the server must be able to reach the machine Blender is running on.

Running Claude Code **locally** in this repo, everything is on one machine and
`.mcp.json` works as-is. Running Claude Code **on the web**, the session lives in
a cloud container and `localhost` is that container, not your desktop — it has no
Blender to connect to, so the Blender tools will not appear.

> The addon executes arbitrary Python sent over that socket and has no
> authentication. Do not port-forward `9876` to the public internet to bridge a
> cloud session to your desktop.

For web sessions, build scenes with the scripts in `blender/` instead and run
them locally.

## One-time setup (on your machine)

1. Install the addon into Blender's user addons folder:

   ```sh
   uvx mcp-for-blender install-addon
   ```

   If it reports that no addons directory was found, either set
   `BLENDERMCP_ADDONS_DIR` to your Blender `scripts/addons` path and rerun, or
   download `addon.py` from the repo and use
   **Edit → Preferences → Add-ons → Install…**

2. In Blender, go to **Edit → Preferences → Add-ons**, search for
   **Interface: MCP for Blender**, and enable it.

## Each session

1. Start Blender.
2. In the 3D View, press **N** to open the sidebar.
3. Open the **MCP for Blender** tab.
4. Tick the Capabilities you want to allow.
5. Click **Connect to Claude**.
6. Run `claude` from this repo — `.mcp.json` launches the server automatically.

Check the connection by asking Claude to describe the current scene.

## Overrides

`BLENDER_HOST` and `BLENDER_PORT` override the default `localhost:9876`.
