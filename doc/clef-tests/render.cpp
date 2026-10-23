#include "c_wrapper.h"
#include "horizontalaligner.h"
#include "layer.h"
#include "keysig.h"
#include "layerelement.h"
#include "measure.h"
#include "staff.h"
#include "toolkit.h"
#include "vrv.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

class ObservedToolkit : public vrv::Toolkit {
public:
    void observePrefixes(vrv::Object *object = nullptr)
    {
        if (!object) object = &m_doc;
        if (auto *layer = dynamic_cast<vrv::Layer *>(object)) {
            auto *key = layer->GetStaffDefKeySig();
            auto *staff = dynamic_cast<vrv::Staff *>(layer->GetFirstAncestor(vrv::STAFF));
            auto *measure = layer->GetFirstAncestor(vrv::MEASURE);
            if (key && staff && measure && key->GetAlignment()) {
                const auto time = key->GetAlignment()->GetTime();
                std::cout << "prefix\t" << measure->GetID() << '\t' << staff->GetN() << '\t' << layer->GetN()
                          << '\t' << key->GetID() << '\t' << key->GetAccidCount() << '\t'
                          << static_cast<int>(key->GetAccidType()) << '\t' << time.GetNumerator() << '/'
                          << time.GetDenominator() << '\t' << static_cast<int>(key->GetScoreDefRole()) << '\n';
            }
        }
        for (auto *child : object->GetChildren()) observePrefixes(child);
    }

    void observe(vrv::Object *object = nullptr)
    {
        if (!object) object = &m_doc;
        if (auto *element = dynamic_cast<vrv::LayerElement *>(object)) {
            auto *alignment = element->GetAlignment();
            auto *staff = dynamic_cast<vrv::Staff *>(element->GetFirstAncestor(vrv::STAFF));
            auto *layer = dynamic_cast<vrv::Layer *>(element->GetFirstAncestor(vrv::LAYER));
            auto *measure = element->GetFirstAncestor(vrv::MEASURE);
            if (staff && layer && measure) {
                std::cout << element->GetID() << '\t' << element->GetClassName() << '\t' << measure->GetID() << '\t'
                          << staff->GetN() << '\t' << layer->GetN() << '\t';
                if (alignment)
                    std::cout << alignment->GetTime().GetNumerator() << '/' << alignment->GetTime().GetDenominator();
                else
                    std::cout << "none";
                const auto duration = element->GetAlignmentDuration();
                std::cout << '\t' << duration.GetNumerator() << '/' << duration.GetDenominator() << '\n';
            }
        }
        for (auto *child : object->GetChildren()) observe(child);
    }
};

int main(int argc, char **argv)
{
    if (argc != 5) return 2;
    const std::string input(std::istreambuf_iterator<char>(std::cin), {});
    std::ifstream optionsFile(argv[3]);
    const std::string options(std::istreambuf_iterator<char>(optionsFile), {});
    const std::string mode(argv[2]);
    if (mode.starts_with("observer")) {
        vrv::SetDefaultResourcePath(argv[1]);
        ObservedToolkit toolkit;
        if (!toolkit.SetOptions(options) || !toolkit.LoadData(input)) return 3;
        const std::string svg = toolkit.RenderToSVG(1, false);
        if (mode == "observer-svg")
            std::cout << svg;
        else if (mode == "observer-mei")
            std::cout << toolkit.GetMEI("{\"scoreBased\":true,\"basic\":false,\"removeIds\":false}");
        else if (mode == "observer-prefix")
            toolkit.observePrefixes();
        else
            toolkit.observe();
    }
    else {
        void *toolkit = vrvToolkit_constructorResourcePath(argv[1]);
        if (!vrvToolkit_setOptions(toolkit, options.c_str()) || !vrvToolkit_loadData(toolkit, input.c_str())) return 3;
        if (mode == "mei")
            std::cout << vrvToolkit_getMEI(toolkit, "{\"scoreBased\":true,\"basic\":false,\"removeIds\":false}");
        else if (mode == "options")
            std::cout << vrvToolkit_getOptions(toolkit);
        else
            std::cout << vrvToolkit_renderToSVG(toolkit, 1, false);
        vrvToolkit_destructor(toolkit);
    }
}
