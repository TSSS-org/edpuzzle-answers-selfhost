//Copyright (C) 2026 ading2210
//see README.md for more information

//this script mainly just serves to load the rest of the program

let mirrors = ["https://edpuzzle.hgci.org", "https://edpuzzle.librecheats.net"];

async function try_mirror(mirror) {
  let r = await fetch(mirror + "/open.js", {cache: "no-cache"});
  let script = await r.text();
  window.base_url = mirror;
  eval(script);
}

async function init() {
  if (window.location.hostname === "localhost") {
    alert("To use this, drag this button into your bookmarks bar. Then, run it when you're on an Edpuzzle assignment.");
    return;
  }
  try {
    let r = await fetch("http://localhost:8080/open.js", {cache: "no-cache"});
    let script = await r.text();
    window.base_url = "http://localhost:8080";
    eval(script);
  } catch {
    alert("Error: Could not connect to local server. Make sure it's running on localhost:8080.");
  }
}
init();
