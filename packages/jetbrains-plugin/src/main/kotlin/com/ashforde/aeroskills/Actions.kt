package com.ashforde.aeroskills

import com.intellij.ide.BrowserUtil
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.ide.CopyPasteManager
import java.awt.datatransfer.StringSelection

/** Copies the MCP registration JSON for JetBrains AI Assistant / Junie. */
class CopyMcpConfigAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val json = """
            {
              "servers": {
                "aero-agent-skills": {
                  "type": "stdio",
                  "command": "npx",
                  "args": ["-y", "aero-agent-skills", "mcp"]
                }
              }
            }
        """.trimIndent()
        CopyPasteManager.getInstance().setContents(StringSelection(json))
        com.intellij.openapi.ui.Messages.showInfoMessage(
            e.project,
            "MCP config copied.\n\nPaste it in:\nSettings | Tools | AI Assistant | Model Context Protocol (MCP) | Add\n(or Junie MCP Settings).\n\nRequires Node.js (npx) on PATH.",
            "Aero Agent Skills — MCP config"
        )
    }
}

/** Copies the Agent Skills external-registry URL for the AI Assistant Skills Manager. */
class CopyRegistryUrlAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val url = "https://github.com/ashfordeOU/aero-agent-skills"
        CopyPasteManager.getInstance().setContents(StringSelection(url))
        com.intellij.openapi.ui.Messages.showInfoMessage(
            e.project,
            "Registry URL copied.\n\nAdd it in:\nSettings | Tools | AI Assistant | Skills\n→ Manage External Registries → Add\n\nAll 330+ skills become browsable + installable in the Skills Manager.",
            "Aero Agent Skills — registry"
        )
    }
}

/** Opens the public docs / harness guide in the browser. */
class OpenDocsAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        BrowserUtil.browse("https://ashforde.org/aeroagentskills")
    }
}
