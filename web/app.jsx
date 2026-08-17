const { useState, useEffect, useMemo } = React;

function App() {
  const [datasets, setDatasets] = useState([]);
  const [totalGlobal, setTotalGlobal] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState('rosario_secundario');
  const [zones, setZones] = useState([]);
  
  const [properties, setProperties] = useState([]);
  const [totalMatches, setTotalMatches] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [stats, setStats] = useState({ avg_m2_usd: 0, venta_count: 0, alquiler_count: 0 });
  const [loading, setLoading] = useState(true);

  // Filtros
  const [search, setSearch] = useState('');
  const [operacion, setOperacion] = useState('todas');
  const [tipo, setTipo] = useState('todos');
  const [zona, setZona] = useState('todas');
  const [minPrecio, setMinPrecio] = useState('');
  const [maxPrecio, setMaxPrecio] = useState('');
  const [sortBy, setSortBy] = useState('id');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Paginación y Vista
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(24);
  const [viewMode, setViewMode] = useState('grid');
  const [selectedProperty, setSelectedProperty] = useState(null);

  // 1. Cargar lista de datasets
  useEffect(() => {
    fetch('/api/datasets')
      .then(res => res.json())
      .then(data => {
        setDatasets(data.datasets || []);
        setTotalGlobal(data.total_global || 0);
      })
      .catch(err => console.error("Error al cargar datasets:", err));
  }, []);

  // 2. Cargar zonas cuando cambia el dataset
  useEffect(() => {
    fetch(`/api/zones?dataset=${selectedDataset}`)
      .then(res => res.json())
      .then(data => {
        setZones(data.zonas || []);
        setZona('todas');
        setPage(1);
      })
      .catch(err => console.error("Error al cargar zonas:", err));
  }, [selectedDataset]);

  // 3. Cargar propiedades filtradas y paginadas
  const fetchProperties = () => {
    setLoading(true);
    const params = new URLSearchParams({
      dataset: selectedDataset,
      page: page,
      limit: limit,
      search: search,
      operacion: operacion,
      tipo: tipo,
      zona: zona,
      sort_by: sortBy,
      sort_order: sortOrder
    });

    if (minPrecio) params.append('min_precio', minPrecio);
    if (maxPrecio) params.append('max_precio', maxPrecio);

    fetch(`/api/properties?${params.toString()}`)
      .then(res => res.json())
      .then(data => {
        setProperties(data.items || []);
        setTotalMatches(data.total || 0);
        setTotalPages(data.total_pages || 1);
        setStats(data.stats || { avg_m2_usd: 0, venta_count: 0, alquiler_count: 0 });
        setLoading(false);
      })
      .catch(err => {
        console.error("Error al cargar propiedades:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchProperties();
  }, [selectedDataset, page, limit, operacion, tipo, zona, sortBy, sortOrder]);

  // Manejador de búsqueda con tecla Enter o botón
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchProperties();
  };

  // Exportar a CSV
  const exportToCSV = () => {
    if (!properties.length) return;
    const headers = ["ID", "Direccion", "Zona", "Tipo", "Operacion", "Precio", "Moneda", "m2", "USD_m2", "Dormitorios", "Antiguedad", "Fuente", "URL"];
    const rows = properties.map(p => [
      p.id_propia,
      `"${(p.direccion || '').replace(/"/g, '""')}"`,
      `"${p.zona || ''}"`,
      p.tipo,
      p.operacion,
      p.precio,
      p.moneda,
      p.m2,
      p.valor_m2,
      p.dormitorios,
      p.antiquity,
      p.fuente,
      p.url
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `export_${selectedDataset}_p${page}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const currentDatasetMeta = useMemo(() => {
    return datasets.find(d => d.id === selectedDataset) || {};
  }, [datasets, selectedDataset]);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      
      {/* HEADER SUPERIOR CON TITULO Y CONTADOR GLOBAL */}
      <header className="sticky top-0 z-30 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 text-xl font-bold shadow-lg shadow-emerald-500/20">
              <i className="fa-solid fa-building"></i>
            </div>
            <div>
              <h1 className="font-heading font-extrabold text-xl text-white tracking-tight flex items-center gap-2">
                Explorador Inmobiliario Nacional
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  React 18 + API
                </span>
              </h1>
              <p className="text-xs text-slate-400">Plataforma de Navegación Masiva de Scraping en Tiempo Real</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="bg-slate-800/80 border border-slate-700 px-4 py-2 rounded-xl flex items-center gap-3">
              <i className="fa-solid fa-database text-emerald-400 text-sm"></i>
              <div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">Red de Cachés</div>
                <div className="text-sm font-bold text-white font-heading">{totalGlobal.toLocaleString()} <span className="text-xs text-slate-400 font-normal">inmuebles</span></div>
              </div>
            </div>

            <button 
              onClick={exportToCSV}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-md shadow-emerald-600/20"
            >
              <i className="fa-solid fa-file-csv text-sm"></i>
              Exportar CSV
            </button>
          </div>
        </div>
      </header>

      {/* CONTENIDO PRINCIPAL */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* SELECCION DE DATASETS / CIUDADES */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <i className="fa-solid fa-city text-emerald-400"></i> Seleccionar Ciudad / Volumen de Scraping ({datasets.length})
            </h2>
          </div>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {datasets.map(ds => {
              const isSelected = ds.id === selectedDataset;
              return (
                <button
                  key={ds.id}
                  onClick={() => {
                    setSelectedDataset(ds.id);
                    setPage(1);
                  }}
                  className={`p-3 rounded-xl border text-left transition relative overflow-hidden flex flex-col justify-between ${
                    isSelected 
                      ? 'bg-slate-800 border-emerald-500 ring-2 ring-emerald-500/20 text-white shadow-lg' 
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-0 right-0 w-2 h-2 bg-emerald-500 rounded-full m-2"></div>
                  )}
                  <div className="text-lg mb-1">{ds.icon}</div>
                  <div className="font-heading font-bold text-xs text-white truncate">{ds.ciudad}</div>
                  <div className="text-[10px] text-slate-400 truncate">{ds.label}</div>
                  <div className="mt-2 flex items-center justify-between text-[10px]">
                    <span className="font-semibold text-emerald-400">{ds.total.toLocaleString()} props</span>
                    <span className="text-slate-500">{ds.size_mb} MB</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* BARRA DE METRICAS KPI */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-card p-4 rounded-2xl">
            <div className="text-xs font-medium text-slate-400">Resultados Filtrados</div>
            <div className="text-2xl font-bold font-heading text-white mt-1">
              {loading ? <span className="animate-pulse text-slate-600">...</span> : totalMatches.toLocaleString()}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">de {currentDatasetMeta.label || 'Dataset seleccionado'}</div>
          </div>

          <div className="glass-card p-4 rounded-2xl">
            <div className="text-xs font-medium text-slate-400">Precio Promedio USD/m²</div>
            <div className="text-2xl font-bold font-heading text-emerald-400 mt-1">
              {loading ? <span className="animate-pulse text-slate-600">...</span> : `$${stats.avg_m2_usd} USD`}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Calculado sobre venta en USD</div>
          </div>

          <div className="glass-card p-4 rounded-2xl">
            <div className="text-xs font-medium text-slate-400">Operación: Venta vs Alquiler</div>
            <div className="text-2xl font-bold font-heading text-teal-300 mt-1">
              {loading ? <span className="animate-pulse text-slate-600">...</span> : `${stats.venta_count.toLocaleString()} / ${stats.alquiler_count.toLocaleString()}`}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {stats.venta_count + stats.alquiler_count > 0 
                ? `${round((stats.venta_count / (stats.venta_count + stats.alquiler_count)) * 100, 1)}% Venta` 
                : '0%'}
            </div>
          </div>

          <div className="glass-card p-4 rounded-2xl">
            <div className="text-xs font-medium text-slate-400">Paginación Activa</div>
            <div className="text-2xl font-bold font-heading text-white mt-1">
              Página {page} <span className="text-sm font-normal text-slate-500">de {totalPages}</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1">{limit} elementos por página</div>
          </div>
        </section>

        {/* PANEL DE FILTROS AVANZADOS */}
        <section className="glass-card p-4 rounded-2xl space-y-4">
          <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
            <div className="flex-1 relative">
              <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
              <input
                type="text"
                placeholder="Buscar por calle, dirección, barrio o ID..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
            </div>
            <button
              type="submit"
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-medium text-xs px-5 py-2.5 rounded-xl transition"
            >
              Buscar
            </button>
          </form>

          {/* CONTROLES DE FILTRADO SECUNDARIOS */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 pt-2 border-t border-slate-800/80">
            
            {/* Operacion */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Operación</label>
              <select
                value={operacion}
                onChange={e => { setOperacion(e.target.value); setPage(1); }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="todas">Todas</option>
                <option value="venta">Venta</option>
                <option value="alquiler">Alquiler</option>
              </select>
            </div>

            {/* Tipo */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Tipo Inmueble</label>
              <select
                value={tipo}
                onChange={e => { setTipo(e.target.value); setPage(1); }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="todos">Todos</option>
                <option value="departamento">Departamento</option>
                <option value="casa">Casa</option>
                <option value="ph">PH</option>
              </select>
            </div>

            {/* Zona */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Barrio / Zona</label>
              <select
                value={zona}
                onChange={e => { setZona(e.target.value); setPage(1); }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="todas">Todas las zonas</option>
                {zones.map(z => (
                  <option key={z} value={z}>{z}</option>
                ))}
              </select>
            </div>

            {/* Ordenar por */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Ordenar por</label>
              <select
                value={sortBy}
                onChange={e => { setSortBy(e.target.value); setPage(1); }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="id">ID Propia</option>
                <option value="precio">Precio Total</option>
                <option value="valor_m2">Valor USD/m²</option>
                <option value="m2">Superficie m²</option>
                <option value="dormitorios">Dormitorios</option>
              </select>
            </div>

            {/* Orden (Asc/Desc) */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Dirección Orden</label>
              <select
                value={sortOrder}
                onChange={e => { setSortOrder(e.target.value); setPage(1); }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="desc">Mayor a Menor (Desc)</option>
                <option value="asc">Menor a Mayor (Asc)</option>
              </select>
            </div>

            {/* Vista (Grid/Tabla) */}
            <div>
              <label className="block text-[10px] font-bold uppercase text-slate-400 mb-1">Modo de Vista</label>
              <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`flex-1 py-1 text-xs rounded font-medium transition ${viewMode === 'grid' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  <i className="fa-solid fa-border-all"></i>
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`flex-1 py-1 text-xs rounded font-medium transition ${viewMode === 'table' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  <i className="fa-solid fa-list"></i>
                </button>
              </div>
            </div>

          </div>
        </section>

        {/* LISTADO DE PROPIEDADES EN VISTA GRID O TABLA */}
        <section>
          {loading ? (
            <div className="py-20 text-center space-y-3">
              <div className="inline-block w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm text-slate-400">Cargando lote de propiedades del cache masivo...</p>
            </div>
          ) : properties.length === 0 ? (
            <div className="py-20 text-center glass-card rounded-2xl space-y-3">
              <i className="fa-solid fa-folder-open text-4xl text-slate-600"></i>
              <p className="text-base text-slate-300 font-medium">No se encontraron propiedades con los filtros seleccionados.</p>
              <p className="text-xs text-slate-500">Prueba ajustando el texto de búsqueda o cambiando el barrio.</p>
            </div>
          ) : viewMode === 'grid' ? (
            /* VISTA TARJETAS (GRID) */
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {properties.map(p => (
                <div
                  key={p.id_propia}
                  className="glass-card glass-card-hover rounded-2xl p-4 flex flex-col justify-between space-y-3 cursor-pointer group"
                  onClick={() => setSelectedProperty(p)}
                >
                  <div>
                    {/* Badge Operacion & Tipo */}
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] uppercase tracking-wider ${
                        p.operacion === 'venta' 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}>
                        {p.operacion}
                      </span>
                      <span className="text-slate-400 text-[11px] font-medium flex items-center gap-1">
                        <i className="fa-solid fa-building text-[10px]"></i> {p.tipo}
                      </span>
                    </div>

                    {/* Direccion */}
                    <h3 className="font-heading font-bold text-sm text-white group-hover:text-emerald-400 transition line-clamp-2">
                      {p.direccion}
                    </h3>
                    
                    <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                      <i className="fa-solid fa-location-dot text-slate-500 text-[10px]"></i> {p.zona}
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 space-y-2">
                    {/* Precio Principal */}
                    <div className="flex items-baseline justify-between">
                      <div className="text-lg font-heading font-extrabold text-white">
                        {p.moneda} {p.precio?.toLocaleString()}
                      </div>
                      {p.valor_m2 && (
                        <div className="text-xs font-semibold text-emerald-400">
                          ${p.valor_m2} USD/m²
                        </div>
                      )}
                    </div>

                    {/* Especificaciones m2, dorms, antiguedad */}
                    <div className="grid grid-cols-3 gap-1 text-[11px] text-slate-400 text-center bg-slate-900/80 rounded-lg p-1.5 border border-slate-800">
                      <div>
                        <div className="text-white font-bold">{p.m2}</div>
                        <div className="text-[9px] text-slate-500">m² sup</div>
                      </div>
                      <div>
                        <div className="text-white font-bold">{p.dormitorios}</div>
                        <div className="text-[9px] text-slate-500">dorms</div>
                      </div>
                      <div>
                        <div className="text-white font-bold">{p.antiquity || 0}</div>
                        <div className="text-[9px] text-slate-500">años ant</div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* VISTA TABLA (DENSE TABLE) */
            <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] font-bold border-b border-slate-800">
                    <tr>
                      <th className="p-3">ID</th>
                      <th className="p-3">Dirección / Inmueble</th>
                      <th className="p-3">Barrio</th>
                      <th className="p-3">Tipo</th>
                      <th className="p-3">Operación</th>
                      <th className="p-3">Precio Total</th>
                      <th className="p-3">Valor USD/m²</th>
                      <th className="p-3">m²</th>
                      <th className="p-3">Dorms</th>
                      <th className="p-3">Fuente</th>
                      <th className="p-3 text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {properties.map(p => (
                      <tr key={p.id_propia} className="hover:bg-slate-800/40 transition">
                        <td className="p-3 font-mono text-slate-400">#{p.id_propia}</td>
                        <td className="p-3 font-medium text-white max-w-xs truncate">{p.direccion}</td>
                        <td className="p-3 text-slate-300">{p.zona}</td>
                        <td className="p-3 text-slate-400">{p.tipo}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${
                            p.operacion === 'venta' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                          }`}>
                            {p.operacion}
                          </span>
                        </td>
                        <td className="p-3 font-bold text-white">{p.moneda} {p.precio?.toLocaleString()}</td>
                        <td className="p-3 text-emerald-400 font-semibold">${p.valor_m2}</td>
                        <td className="p-3 text-slate-300">{p.m2} m²</td>
                        <td className="p-3 text-slate-300">{p.dormitorios}</td>
                        <td className="p-3 text-slate-500">{p.fuente}</td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => setSelectedProperty(p)}
                            className="bg-slate-800 hover:bg-slate-700 text-white text-[11px] px-2.5 py-1 rounded transition"
                          >
                            Inspeccionar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        {/* PAGINADOR */}
        <section className="flex flex-col sm:flex-row items-center justify-between gap-4 glass-card p-4 rounded-2xl">
          <div className="text-xs text-slate-400">
            Mostrando página <span className="text-white font-bold">{page}</span> de <span className="text-white font-bold">{totalPages}</span> ({totalMatches.toLocaleString()} inmuebles filtrados)
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(1)}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800"
            >
              <i className="fa-solid fa-angles-left"></i>
            </button>
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800"
            >
              Anterior
            </button>

            <span className="text-xs px-2 text-slate-300 font-mono">{page}</span>

            <button
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800"
            >
              Siguiente
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(totalPages)}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800"
            >
              <i className="fa-solid fa-angles-right"></i>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Por página:</span>
            <select
              value={limit}
              onChange={e => { setLimit(Number(e.target.value)); setPage(1); }}
              className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none"
            >
              <option value={24}>24</option>
              <option value={48}>48</option>
              <option value={96}>96</option>
              <option value={200}>200</option>
            </select>
          </div>
        </section>

      </main>

      {/* DRAWER / MODAL INSPECTOR DE PROPIEDAD */}
      {selectedProperty && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-end animate-fadeIn">
          <div className="w-full max-w-xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto p-6 space-y-6 shadow-2xl flex flex-col justify-between">
            <div className="space-y-6">
              
              {/* Header Modal */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                <div>
                  <span className="text-xs font-mono text-emerald-400 font-bold">ID Propia #{selectedProperty.id_propia}</span>
                  <h2 className="text-xl font-heading font-extrabold text-white mt-1">{selectedProperty.direccion}</h2>
                  <p className="text-xs text-slate-400 flex items-center gap-1 mt-1">
                    <i className="fa-solid fa-location-dot text-slate-500"></i> {selectedProperty.zona}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedProperty(null)}
                  className="w-8 h-8 rounded-full bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center transition"
                >
                  <i className="fa-solid fa-xmark"></i>
                </button>
              </div>

              {/* Tarjeta de Valuacion */}
              <div className="glass-card p-4 rounded-2xl space-y-3 bg-gradient-to-br from-slate-900 to-slate-800">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Métricas de Valuación Mercado</div>
                <div className="flex items-baseline justify-between">
                  <div className="text-2xl font-heading font-black text-white">
                    {selectedProperty.moneda} {selectedProperty.precio?.toLocaleString()}
                  </div>
                  <div className="text-lg font-bold text-emerald-400">
                    ${selectedProperty.valor_m2} USD/m²
                  </div>
                </div>
              </div>

              {/* Atributos Tecnicos */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Superficie Total</span>
                  <span className="text-white font-bold text-base">{selectedProperty.m2} m²</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Dormitorios</span>
                  <span className="text-white font-bold text-base">{selectedProperty.dormitorios} dorms</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Antigüedad Estimada</span>
                  <span className="text-white font-bold text-base">{selectedProperty.antiquity || 0} años</span>
                </div>
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Fuente Portal</span>
                  <span className="text-white font-bold text-base">{selectedProperty.fuente}</span>
                </div>
              </div>

              {/* Geolocalizacion & Mapa */}
              {selectedProperty.lat && selectedProperty.lon && (
                <div className="space-y-2">
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Geolocalización GPS</div>
                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-mono">Lat: {selectedProperty.lat}, Lon: {selectedProperty.lon}</span>
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${selectedProperty.lat},${selectedProperty.lon}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-emerald-400 font-bold hover:underline flex items-center gap-1"
                    >
                      Ver en Google Maps <i className="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                    </a>
                  </div>
                </div>
              )}

              {/* Inspector JSON Estructurado */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Estructura de Datos JSON Completa</div>
                <pre className="bg-slate-950 p-4 rounded-xl text-[11px] font-mono text-emerald-300 overflow-x-auto border border-slate-800 max-h-60">
                  {JSON.stringify(selectedProperty, null, 2)}
                </pre>
              </div>

            </div>

            {/* Footer Modal con Link Directo */}
            <div className="pt-4 border-t border-slate-800">
              <a
                href={selectedProperty.url}
                target="_blank"
                rel="noreferrer"
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm py-3 rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20"
              >
                Abrir Publicación en Portal Original <i className="fa-solid fa-arrow-up-right-from-square"></i>
              </a>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

// Auxiliar redondeo
function round(num, decimals) {
  return Number(Math.round(num + 'e' + decimals) + 'e-' + decimals);
}

// Renderizar app React
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
