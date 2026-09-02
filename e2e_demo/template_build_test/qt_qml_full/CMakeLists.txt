cmake_minimum_required(VERSION 3.16)

project(E2ESettingsQML LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# Qt6 查找
find_package(Qt6 6.0 REQUIRED COMPONENTS Quick QuickControls2 QuickLayouts)
message(STATUS "Using Qt ${Qt6_VERSION}")

qt6_add_executable(E2ESettings
    main.cpp
)

qt6_add_qml_module(E2ESettings
    URI E2ESettings
    VERSION 1.0
    QML_FILES
        main.qml
)

target_link_libraries(E2ESettings PRIVATE
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::QuickLayouts
)

install(TARGETS E2ESettings
    BUNDLE  DESTINATION .
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
)
