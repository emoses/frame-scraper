import {
  createConnection,
  subscribeEntities,
    createLongLivedTokenAuth,
    HassEntities,
} from "hass-websocket";

import "jsr:@std/dotenv/load";

// Learn more at https://docs.deno.com/runtime/manual/examples/module_metadata#concepts
if (import.meta.main) {
    const token = Deno.env.get("HASS_TOKEN");
    if (!token) {
        console.error("Missing HASS_TOKEN env var");
        Deno.exit(1);
    }

    const url = Deno.env.get("HASS_URL");
    if (!url) {
        console.error("Missing HASS_URL env var");
        Deno.exit(1);
    }

    const auth = createLongLivedTokenAuth(url, token);

    const conn = await createConnection({auth});
    subscribeEntities(conn, (st: HassEntities) => console.log(st["input_boolean.tv_art_mode"]));
}
