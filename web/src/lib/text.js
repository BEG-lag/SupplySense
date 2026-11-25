// CFE y otras fuentes publican títulos en MAYÚSCULAS. Para leerlos mejor se muestran en tipo
// oración, conservando siglas, claves con números y nombres propios frecuentes. El dato
// original no cambia (se exporta tal cual).

const ACRONYMS = new Set(`CFE PEMEX PEP PTI CENACE CENAGAS IMP SENER ASEA CNE CRE CNH INEEL CONUEE
LP GNL GLP PLC SCADA UPS CCTV TI TIC IMSS ISSSTE IVA NOM ISO API ASME ANSI HP KV MVA KW MW KVA
II III IV VI VII VIII IX XI XII XIII SA CV RL SC SAPI DE.CV GPS LED AC DC SF6 TR CT CC LT SE
EPP OSD UC CDMX EDO USD MXN SIC SICT SAT DOF ID LIBRE`.split(/\s+/))

const PROPER = `México Campeche Tabasco Veracruz Oaxaca Jalisco Sonora Yucatán Chiapas Chihuahua Coahuila
Michoacán Puebla Guerrero Hidalgo Nayarit Sinaloa Tamaulipas Zacatecas Durango Morelos Querétaro
Guanajuato Colima Tlaxcala Baja California Monterrey Guadalajara Carmen Bocas Salina Cruz Tula
Cadereyta Minatitlán Salamanca Tuxpan Coatzacoalcos Villahermosa Mérida Cancún Tijuana Mexicali
Hermosillo Pacífico Golfo Bajío Laguna Valle Toluca Reynosa Matamoros Tampico Madero Altamira
Acapulco Manzanillo Mazatlán Culiacán Torreón Saltillo Aguascalientes León Morelia Pachuca
Cuernavaca Xalapa Poza Rica Paraíso Ixtoc Cantarell Ku Maloob Zaap Abkatún Akal Chicontepec
Distribución Transmisión Generación Suministro Básico Telecomunicaciones Internet Todos`
  .split(/\s+/)
  .reduce((map, word) => map.set(word.toLowerCase(), word), new Map())

// Palabras de PROPER que solo son nombre propio pegadas a CFE ("CFE Distribución").
const AFTER_CFE = new Set(['distribución', 'transmisión', 'generación', 'suministro', 'básico', 'telecomunicaciones', 'internet', 'todos'])

function isShouting(text) {
  const letters = text.replace(/[^A-Za-zÁÉÍÓÚÑÜáéíóúñü]/g, '')
  if (letters.length < 8) return false
  const upper = letters.replace(/[^A-ZÁÉÍÓÚÑÜ]/g, '').length
  return upper / letters.length > 0.75
}

export function displayTitle(text) {
  if (!text || !isShouting(text)) return text
  const tokens = text.split(/(\s+|[,;:()/"“”.])/)
  let started = false
  let prev = ''
  return tokens.map((tok) => {
    if (!tok || /^\s+$/.test(tok) || /^[,;:()/"“”.]$/.test(tok)) return tok
    let out
    const bare = tok.replace(/[^A-Za-zÁÉÍÓÚÑÜ0-9&-]/g, '')
    if (ACRONYMS.has(bare) || /\d/.test(tok) || (bare.length <= 3 && /^[A-Z]+$/.test(bare) && !/^(DE|LA|EL|EN|Y|A|O|U|AL|DEL|LAS|LOS|CON|POR|SIN|SU|SUS|UN|UNA|QUE|SE|NO|ES|E|SUR|MAR|GAS|RED|LUZ|VIA|VÍA|SAL|SOL|DIA|DÍA|MES|AÑO|UNO|DOS|SEIS|OBRA|AGUA|PARA|ZONA|ALTA|BAJA|MEDIA|PLAN|ACERO|TUBO|AIRE|ARCO|EJE|PIE|FIN|VAN|VEZ|OTRO|OTRA|MAS|MÁS)$/.test(bare))) {
      out = tok
    } else {
      const lower = tok.toLowerCase()
      const proper = PROPER.get(lower)
      if (proper && (!AFTER_CFE.has(lower) || prev === 'CFE')) out = proper
      else out = lower
    }
    if (!started && /[a-záéíóúñ]/.test(out.charAt(0))) {
      out = out.charAt(0).toUpperCase() + out.slice(1)
    }
    if (/[A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9]/.test(tok)) started = true
    prev = bare
    return out
  }).join('')
}
