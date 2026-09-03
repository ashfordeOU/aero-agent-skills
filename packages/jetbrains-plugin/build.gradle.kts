import org.jetbrains.intellij.platform.gradle.TestFrameworkType

plugins {
    id("java")
    id("org.jetbrains.kotlin.jvm") version "2.0.21"
    id("org.jetbrains.intellij.platform") version "2.1.0"
}

group = "com.ashforde.aeroskills"
version = "1.3.0"

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

kotlin {
    jvmToolchain(21)
}

dependencies {
    intellijPlatform {
        // Supports IntelliJ IDEA, WebStorm, PyCharm, and all other JetBrains IDEs
        intellijIdeaCommunity("2024.2")
        pluginVerifier()
        zipSigner()
        instrumentationTools()
        testFramework(TestFrameworkType.Platform)
    }
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.0")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

intellijPlatform {
    projectName = "aero-agent-skills"

    pluginConfiguration {
        id = "com.ashforde.aeroskills"
        name = "Aero Agent Skills"
        version = "1.0.0"

        description = """
            <p><b>Aero Agent Skills</b> — the aerospace knowledge layer for AI agents.</p>
            <p>Standards-mapped skills (ECSS · DO-178C · NASA · ARP4754A · FAR/CS) that give your
            AI assistant the certification process — not just the acronyms. Every skill is a
            verified workflow: the steps, the pitfalls, the gates, and the human sign-off.</p>
            <ul>
                <li><b>330+ verified skills</b> across aerodynamics, avionics, flight mechanics,
                    GNC/autonomy, propulsion, structures, space systems, and vehicle design</li>
                <li><b>Skill catalog browser</b> — search and inspect any skill in the IDE</li>
                <li><b>One-click MCP registration</b> — connect JetBrains AI Assistant / Junie to
                    the deterministic skill router (<code>npx -y aero-agent-skills mcp</code>)</li>
                <li><b>External registry</b> — add the GitHub repo as an Agent Skills registry so
                    the AI Assistant Skills Manager can install skills directly</li>
            </ul>
            <p>Open source, Apache-2.0. Repo: <a href="https://github.com/ashfordeOU/aero-agent-skills">github.com/ashfordeOU/aero-agent-skills</a>.
            Landing page: <a href="https://ashforde.org/aeroagentskills">ashforde.org/aeroagentskills</a>.</p>
        """.trimIndent()

        ideaVersion {
            sinceBuild = "242"
        }
    }

    signing {
        certificateChain = System.getenv("PLUGIN_CERTIFICATE_CHAIN")
        privateKey = System.getenv("PLUGIN_PRIVATE_KEY")
        password = System.getenv("PLUGIN_PRIVATE_KEY_PASSWORD")
    }

    publishing {
        token = System.getenv("PUBLISH_TOKEN")
        hidden = false
    }
}

tasks {
    test {
        useJUnitPlatform()
    }
}
