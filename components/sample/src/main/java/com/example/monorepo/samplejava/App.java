package com.example.monorepo.samplejava;

public final class App {
  private App() {}

  public static void main(String[] args) {
    String name = args.length == 0 ? "monorepo" : args[0];
    System.out.println(Greeting.forName(name));
  }
}
