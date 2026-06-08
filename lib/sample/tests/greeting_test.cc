#include "sample_cpp/greeting.h"

#include <gtest/gtest.h>

namespace {

TEST(GreetingTest, GreetsWorldWhenNameIsEmpty) {
    EXPECT_EQ(sample_cpp::greeting(""), "Hello, world!");
}

TEST(GreetingTest, GreetsNamedUser) {
    EXPECT_EQ(sample_cpp::greeting("Bazel"), "Hello, Bazel!");
}

}  // namespace
