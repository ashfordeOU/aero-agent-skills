package com.ashforde.aeroskills

import javax.swing.JComponent
import javax.swing.JPanel

/** Bridge used by the tool-window factory. */
object CatalogPanelFactory {
    fun create(): JComponent = SkillCatalogPanel()
}
