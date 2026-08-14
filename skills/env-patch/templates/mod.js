'use strict';

function installEnv(profile) {
  const root = globalThis;
  root.window = root;
  root.self = root;
  root.globalThis = root;
  root.__profile__ = profile || root.__profile__ || {};

  if (!root.console) root.console = console;
  if (!root.atob) root.atob = (value) => Buffer.from(String(value), 'base64').toString('binary');
  if (!root.btoa) root.btoa = (value) => Buffer.from(String(value), 'binary').toString('base64');

  // Paste the verified env-patch module bodies below, preserving load order.
  // Recommended order:
  // core/ProfileManager.js -> bom/* -> dom/* -> webapi/* -> ai-generated/*
}

installEnv();

module.exports = {
  installEnv,
};
