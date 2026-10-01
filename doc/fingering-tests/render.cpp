#include "c_wrapper.h"

#include <iostream>
#include <iterator>
#include <string>

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    void *toolkit = vrvToolkit_constructorResourcePath(argv[1]);
    const bool bounds = std::string(argv[2]) == "svg-bounds";
    vrvToolkit_setOptions(toolkit, bounds
            ? "{\"inputFrom\":\"humdrum\",\"breaks\":\"none\",\"svgHtml5\":false,\"svgBoundingBoxes\":true,\"svgContentBoundingBoxes\":true}"
            : "{\"inputFrom\":\"humdrum\",\"breaks\":\"none\",\"svgHtml5\":false}");
    const std::string input(std::istreambuf_iterator<char>(std::cin), {});
    if (!vrvToolkit_loadData(toolkit, input.c_str())) return 3;
    if (std::string(argv[2]) == "mei") {
        std::cout << vrvToolkit_getMEI(toolkit, "{}");
    }
    else {
        std::cout << vrvToolkit_renderToSVG(toolkit, 1, false);
    }
    vrvToolkit_destructor(toolkit);
}
