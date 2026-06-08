package com.example.monorepo.samplejava;

public final class Greeting {
  private Greeting() {}

  public static String forName(String name) {
    String normalized = name == null ? "" : name.trim();
    if (normalized.isEmpty()) {
      normalized = "monorepo";
    }
    return "Hello, " + normalized + " from Java";
  }
}
