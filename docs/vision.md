# Vision and non-goals

KPB makes source builds practical through readable recipes, explicit dependencies and reuse of existing Linux infrastructure. Recipes take inspiration from Arch PKGBUILDs and BSD ports; Git repositories make them reviewable and independently maintainable, including future community repositories.

The aim is working applications with minimal necessary compilation. KPB complements the native package manager and preserves its ownership of host packages/files. It is not a Gentoo clone, a replacement distribution manager or a requirement to rebuild the host toolchain/runtime. Host-bound results are useful even without cross-distribution portability.

PackageKit is the preferred integration direction because it offers a common interface across native package managers. Backend capabilities vary, so a provider abstraction permits approved native adapters without coupling recipe resolution to one service or distribution.

Installation, upgrades/removal, ownership tracking and Git/community repositories are long-term goals. Their existence in this vision is not implementation approval; [decisions.md](decisions.md) defines the current contract and [open decisions](deferred-decisions.md) gate future features.
