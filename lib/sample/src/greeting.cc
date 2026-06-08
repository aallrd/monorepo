#include "sample_cpp/greeting.h"

#include <string>

namespace sample_cpp {

std::string greeting(std::string_view name) {
    if (name.empty()) {
        return "Hello, world!";
    }

    return "Hello, " + std::string(name) + "!";
}

}  // namespace sample_cpp
