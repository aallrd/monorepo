package com.example.monorepo.samplejava;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class GreetingTest {
  @Test
  void greetsProvidedName() {
    assertEquals("Hello, Ada from Java", Greeting.forName("Ada"));
  }

  @Test
  void defaultsBlankNameToMonorepo() {
    assertEquals("Hello, monorepo from Java", Greeting.forName("  "));
  }
}
