package com.ashforde.aeroskills

import com.intellij.ui.components.JBList
import com.intellij.ui.components.JBScrollPane
import com.intellij.util.ui.JBUI
import org.jetbrains.annotations.NonNls
import java.awt.BorderLayout
import java.awt.FlowLayout
import javax.swing.*
import javax.swing.event.DocumentEvent
import javax.swing.event.DocumentListener

/**
 * Skill catalog browser.
 *
 * Ships a static catalog snapshot (families/packs/skills + descriptions) so the
 * IDE panel works offline. The live catalog lives in the public repo's
 * manifest.json (regenerated on every release); this snapshot is refreshed by
 * scripts/gen_visuals.py at build time via the plugin bundle task.
 */
class SkillCatalogPanel : JPanel(BorderLayout()) {

    private val model = DefaultListModel<SkillRow>()
    private val allSkills: List<SkillRow> = loadCatalog()

    private val list = JBList(model)

    init {
        list.cellRenderer = object : DefaultListCellRenderer() {
            override fun getListCellRendererComponent(
                list: JList<*>?,
                value: Any?,
                index: Int,
                isSelected: Boolean,
                cellHasFocus: Boolean
            ): java.awt.Component {
                val c = super.getListCellRendererComponent(list, value, index, isSelected, cellHasFocus)
                if (value is SkillRow) {
                    text = "<html><b>${value.name}</b> — ${value.shortDescription()}</html>"
                }
                return c
            }
        }

        val search = JTextField()
        search.toolTipText = "Search 330+ aerospace skills (name or description)"
        search.document.addDocumentListener(object : DocumentListener {
            override fun insertUpdate(e: DocumentEvent?) = filter(search.text)
            override fun removeUpdate(e: DocumentEvent?) = filter(search.text)
            override fun changedUpdate(e: DocumentEvent?) = filter(search.text)
        })

        filter("")

        val hint = JLabel(
            "<html><small>Install: <b>Settings | Tools | AI Assistant | Skills</b> → Manage External " +
                "Registries → add <code>https://github.com/ashfordeOU/aero-agent-skills</code>. " +
                "Or connect MCP: Tools → <b>Copy MCP Server Config</b>.</small></html>"
        )
        hint.border = JBUI.Borders.empty(6)

        add(search, BorderLayout.NORTH)
        add(JBScrollPane(list), BorderLayout.CENTER)
        add(hint, BorderLayout.SOUTH)
    }

    private fun filter(query: String) {
        model.clear()
        val q = query.trim().lowercase()
        allSkills
            .filter { q.isEmpty() || it.name.lowercase().contains(q) || it.description.lowercase().contains(q) }
            .take(500)
            .forEach { model.addElement(it) }
        if (model.isEmpty()) {
            model.addElement(SkillRow("(no skills match)", "", ""))
        }
    }

    private companion object {
        @NonNls
        private const val CATALOG_RESOURCE = "/catalog/catalog.json"

        fun loadCatalog(): List<SkillRow> {
            val stream = SkillCatalogPanel::class.java.getResourceAsStream(CATALOG_RESOURCE)
                ?: return listOf(SkillRow("(catalog not bundled)", "Build bundle task to embed catalog.json", ""))
            return try {
                val text = stream.bufferedReader().use { it.readText() }
                parseCatalog(text)
            } catch (e: Exception) {
                listOf(SkillRow("(catalog error: ${e.message})", "", ""))
            }
        }

        fun parseCatalog(json: String): List<SkillRow> {
            // Minimal JSON parse without external deps: {"skills": [{name, family, description}]}
            val rows = ArrayList<SkillRow>()
            val nameRe = Regex("\"name\"\\s*:\\s*\"([^\"]+)\"")
            val descRe = Regex("\"description\"\\s*:\\s*\"([^\"]+)\"")
            val familyRe = Regex("\"family\"\\s*:\\s*\"([^\"]+)\"")
            val itemRe = Regex("\\{([^{}]*)}")
            for (m in itemRe.findAll(json)) {
                val block = m.groupValues[1]
                val name = nameRe.find(block)?.groupValues?.get(1) ?: continue
                val desc = descRe.find(block)?.groupValues?.get(1) ?: ""
                val fam = familyRe.find(block)?.groupValues?.get(1) ?: ""
                rows.add(SkillRow(name, desc, fam))
            }
            return rows
        }
    }
}

/** Lightweight catalog row. */
data class SkillRow(val name: String, val description: String, val family: String) {
    fun shortDescription(): String =
        if (description.length > 90) description.take(90) + "…" else description
}
