#include <iostream>
#include <string_view>

#include "sample_cpp/greeting.h"

int main(int argc, char** argv) {
    const std::string_view name = argc > 1 ? std::string_view(argv[1]) : std::string_view();
    std::cout << sample_cpp::greeting(name) << '\n';
    return 0;
}
