import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import { fmt, qualityHex } from "../lib/format.js";

const CONEXIONES = [
  { from: "afluente", to: "rejillas", kind: "agua" },
  { from: "rejillas", to: "desarenador", kind: "agua" },
  { from: "desarenador", to: "primario", kind: "agua" },
  { from: "primario", to: "anaerobio", kind: "agua" },
  { from: "anaerobio", to: "anoxico", kind: "agua" },
  { from: "anoxico", to: "aerobio", kind: "agua" },
  { from: "aerobio", to: "secundario", kind: "agua" },
  { from: "secundario", to: "desinfeccion", kind: "agua" },
  { from: "desinfeccion", to: "efluente", kind: "agua" },
  { from: "primario", to: "espesador", kind: "lodo", via: [[-6, 1.1, 9.5]] },
  { from: "secundario", to: "espesador", kind: "lodo", via: [[17, 1.1, 9.5]] },
  { from: "espesador", to: "digestor", kind: "lodo" },
  { from: "digestor", to: "deshidratacion", kind: "lodo" },
  { from: "secundario", to: "anaerobio", kind: "recirculacion", via: [[14, 1.5, -7.5]] },
  { from: "aerobio", to: "anoxico", kind: "recirculacion", via: [[11, 1.8, 6.5]] },
  { from: "deshidratacion", to: "afluente", kind: "rechazo", via: [[-36, 1.5, 9.5]] },
];

const ESTILOS_TUBERIA = {
  agua: { color: 0x1d5c78, radio: 0.17, particula: 0x7ce7ff, puntos: 4, velocidad: 0.07 },
  lodo: { color: 0x6b4a22, radio: 0.21, particula: 0xfbbf24, puntos: 3, velocidad: 0.035 },
  recirculacion: { color: 0x9a5b1f, radio: 0.09, particula: 0xf59e0b, puntos: 3, velocidad: 0.05 },
  rechazo: { color: 0x3f4d5e, radio: 0.11, particula: 0x94a3b8, puntos: 2, velocidad: 0.03 },
};

export class PlantScene {
  constructor(container, { onSelect } = {}) {
    this.container = container;
    this.onSelect = onSelect;
    this.units = new Map();
    this.flowDots = [];
    this.waterMaterials = [];
    this.bubbleSystems = [];
    this.toggles = { etiquetas: true, flujos: true, calidad: true, rotacion: false };
    this.selected = null;
    this.flowSpeed = 1;
    this.tween = null;
    this.dragging = false;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color("#050b14");
    this.scene.fog = new THREE.Fog("#050b14", 95, 210);

    this.camera = new THREE.PerspectiveCamera(44, 1, 0.1, 400);
    this.camera.position.set(-4, 62, 60);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.domElement.style.display = "block";
    this.renderer.domElement.style.width = "100%";
    this.renderer.domElement.style.height = "100%";
    container.appendChild(this.renderer.domElement);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.domElement.style.position = "absolute";
    this.labelRenderer.domElement.style.inset = "0";
    this.labelRenderer.domElement.style.pointerEvents = "none";
    this.labelRenderer.domElement.style.overflow = "hidden";
    container.appendChild(this.labelRenderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(4, 0, 6);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.065;
    this.controls.minDistance = 10;
    this.controls.maxDistance = 145;
    this.controls.maxPolarAngle = Math.PI / 2 - 0.04;
    this.controls.screenSpacePanning = false;
    this.controls.update();

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.clock = new THREE.Clock();
    this.waterTexture = this._crearTexturaAgua();

    this._construirEntorno();
    this._crearAnilloSeleccion();
    this._enlazarEventos();

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.resize();

    this._animate = this._animate.bind(this);
    this.raf = requestAnimationFrame(this._animate);
  }

  // ------------------------------------------------------------------
  // Entorno
  // ------------------------------------------------------------------
  _construirEntorno() {
    const cielo = new THREE.Mesh(
      new THREE.SphereGeometry(180, 32, 18),
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        uniforms: {
          topColor: { value: new THREE.Color("#0d2740") },
          bottomColor: { value: new THREE.Color("#040910") },
        },
        vertexShader: `
          varying vec3 vWorld;
          void main() {
            vec4 p = modelMatrix * vec4(position, 1.0);
            vWorld = p.xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          varying vec3 vWorld;
          uniform vec3 topColor;
          uniform vec3 bottomColor;
          void main() {
            float h = normalize(vWorld).y;
            float t = clamp(h * 0.5 + 0.5, 0.0, 1.0);
            gl_FragColor = vec4(mix(bottomColor, topColor, pow(t, 0.7)), 1.0);
          }
        `,
      }),
    );
    this.scene.add(cielo);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(280, 190),
      new THREE.MeshStandardMaterial({
        color: 0x081522,
        roughness: 0.98,
        metalness: 0.02,
      }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.08;
    ground.receiveShadow = true;
    this.scene.add(ground);

    const grid = new THREE.GridHelper(260, 52, 0x1b4a6b, 0x0f2a42);
    grid.material.transparent = true;
    grid.material.opacity = 0.32;
    grid.position.y = 0.01;
    this.scene.add(grid);

    const hemi = new THREE.HemisphereLight(0xbfe8ff, 0x0a1420, 1.1);
    hemi.position.set(0, 50, 0);
    this.scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xffffff, 2.4);
    sun.position.set(-45, 70, 35);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -85;
    sun.shadow.camera.right = 85;
    sun.shadow.camera.top = 70;
    sun.shadow.camera.bottom = -70;
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 220;
    sun.shadow.bias = -0.0004;
    this.scene.add(sun);

    const fill = new THREE.DirectionalLight(0x5cc8ff, 0.7);
    fill.position.set(50, 25, -40);
    this.scene.add(fill);

    this.scene.add(new THREE.AmbientLight(0x8fb8d8, 0.22));

    // Franja de terreno para el tren de lodos
    const patio = new THREE.Mesh(
      new THREE.BoxGeometry(88, 0.22, 22),
      new THREE.MeshStandardMaterial({ color: 0x0d1c2b, roughness: 0.95 }),
    );
    patio.position.set(-2, -0.02, 18);
    patio.receiveShadow = true;
    this.scene.add(patio);

    this.scene.add(this._letrero());
  }

  _letrero() {
    const grupo = new THREE.Group();
    const panel = new THREE.Mesh(
      new THREE.BoxGeometry(7.2, 2.2, 0.18),
      new THREE.MeshStandardMaterial({ color: 0x0b2338, roughness: 0.6, metalness: 0.3 }),
    );
    panel.position.set(-45, 4.2, -7);
    panel.rotation.y = Math.PI / 2.4;
    panel.castShadow = true;
    grupo.add(panel);
    const poste = new THREE.Mesh(
      new THREE.CylinderGeometry(0.18, 0.18, 4.2, 8),
      new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.6, roughness: 0.4 }),
    );
    poste.position.set(-45, 2.1, -7);
    grupo.add(poste);
    return grupo;
  }

  _crearAnilloSeleccion() {
    const geo = new THREE.TorusGeometry(2, 0.08, 8, 48);
    const mat = new THREE.MeshBasicMaterial({
      color: 0x7ce7ff,
      transparent: true,
      opacity: 0.85,
    });
    this.ring = new THREE.Mesh(geo, mat);
    this.ring.rotation.x = -Math.PI / 2;
    this.ring.visible = false;
    this.scene.add(this.ring);
  }

  _crearTexturaAgua() {
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#eaf8ff";
    ctx.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 55; i += 1) {
      const x = Math.random() * 256;
      const y = Math.random() * 256;
      ctx.strokeStyle = `rgba(126, 210, 255, ${0.08 + Math.random() * 0.16})`;
      ctx.lineWidth = 0.6 + Math.random() * 1.6;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.bezierCurveTo(x + 22, y - 10, x + 34, y + 10, x + 58, y + 2);
      ctx.stroke();
    }
    const textura = new THREE.CanvasTexture(canvas);
    textura.wrapS = THREE.RepeatWrapping;
    textura.wrapT = THREE.RepeatWrapping;
    textura.repeat.set(3, 3);
    textura.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
    return textura;
  }

  // ------------------------------------------------------------------
  // Catálogo y unidades
  // ------------------------------------------------------------------
  setCatalog(unidades) {
    this._limpiarUnidades();
    this.catalog = unidades;
    unidades.forEach((u) => this._construirUnidad(u));
    this._construirTuberias();
  }

  _limpiarUnidades() {
    this.units.forEach((ud) => {
      this.scene.remove(ud.group);
      this._disposeObject(ud.group);
    });
    this.units.clear();
    if (this.pipeGroup) {
      this.scene.remove(this.pipeGroup);
      this._disposeObject(this.pipeGroup);
      this.pipeGroup = null;
    }
    this.flowDots = [];
    this.waterMaterials = [];
    this.bubbleSystems = [];
  }

  _material(color, extra = {}) {
    return new THREE.MeshStandardMaterial({
      color,
      roughness: 0.62,
      metalness: 0.16,
      ...extra,
    });
  }

  _agua(color) {
    const mat = new THREE.MeshPhysicalMaterial({
      color,
      map: this.waterTexture,
      transparent: true,
      opacity: 0.9,
      roughness: 0.18,
      metalness: 0.04,
      clearcoat: 0.7,
      clearcoatRoughness: 0.2,
      emissive: new THREE.Color(0x03151f),
      emissiveIntensity: 0.5,
    });
    this.waterMaterials.push(mat);
    return mat;
  }

  _etiqueta(nombre, texto, altura) {
    const el = document.createElement("div");
    el.className = "unit-label";
    el.innerHTML = `<strong>${nombre}</strong><small>${texto}</small>`;
    const obj = new CSS2DObject(el);
    obj.position.set(0, altura, 0);
    return { obj, el };
  }

  _construirUnidad(u) {
    const [w, h, d] = u.dimensiones;
    const [x, y, z] = u.posicion;
    const grupo = new THREE.Group();
    grupo.position.set(x, y, z);
    grupo.userData.unitId = u.id;

    const slab = new THREE.Mesh(
      new THREE.BoxGeometry(w + 3.4, 0.28, d + 3.4),
      this._material(0x112538, { roughness: 0.92, metalness: 0.05 }),
    );
    slab.position.y = -0.14;
    slab.receiveShadow = true;
    grupo.add(slab);

    const ud = {
      ...u,
      group: grupo,
      waterMeshes: [],
      labelEl: null,
      baseColor: u.color,
      cod: null,
    };

    if (u.forma === "cilindro") this._cilindro(grupo, u, ud, w, h, d);
    else if (u.forma === "digestor") this._digestor(grupo, u, ud, w, h);
    else if (u.forma === "tanque") this._tanque(grupo, u, ud, w, h, d);
    else if (u.forma === "edificio") this._edificio(grupo, u, ud, w, h, d);
    else this._canal(grupo, u, ud, w, h, d);

    const alturaEtiqueta =
      {
        primario: h + 4.2,
        anaerobio: h + 2.2,
        anoxico: h + 4.6,
        aerobio: h + 2.2,
        secundario: h + 6.2,
        desinfeccion: h + 2.4,
        efluente: h + 4.6,
        espesador: h + 3.0,
        digestor: h + 2.2,
        deshidratacion: h + 3.6,
      }[u.id] ?? h + 2.3;
    const { obj, el } = this._etiqueta(u.nombre, "sin simulación", alturaEtiqueta);
    grupo.add(obj);
    ud.labelEl = el;

    grupo.traverse((obj3d) => {
      if (obj3d.isMesh) {
        obj3d.castShadow = true;
        obj3d.receiveShadow = true;
      }
    });

    this.scene.add(grupo);
    this.units.set(u.id, ud);
  }

  _cilindro(grupo, u, ud, w, h, d) {
    const r = Math.max(w, d) / 2;
    const pared = new THREE.Mesh(
      new THREE.CylinderGeometry(r, r, h, 48, 1, true),
      this._material(new THREE.Color(u.color), {
        side: THREE.DoubleSide,
        roughness: 0.55,
        metalness: 0.22,
      }),
    );
    pared.position.y = h / 2;
    grupo.add(pared);

    const fondo = new THREE.Mesh(
      new THREE.CylinderGeometry(r, r, 0.3, 48),
      this._material(0x233a4f),
    );
    fondo.position.y = 0.15;
    grupo.add(fondo);

    const borde = new THREE.Mesh(
      new THREE.TorusGeometry(r, 0.12, 8, 56),
      this._material(0x9fb7c9, { metalness: 0.5, roughness: 0.35 }),
    );
    borde.rotation.x = Math.PI / 2;
    borde.position.y = h;
    grupo.add(borde);

    const agua = new THREE.Mesh(
      new THREE.CylinderGeometry(r - 0.36, r - 0.36, h * 0.72, 48),
      this._agua(new THREE.Color(u.color)),
    );
    agua.position.y = 0.15 + (h * 0.72) / 2;
    grupo.add(agua);
    ud.waterMeshes.push(agua);

    // Puente y barandas
    const puente = new THREE.Mesh(
      new THREE.BoxGeometry(r * 2 + 1, 0.12, 0.9),
      this._material(0x94a3b8, { metalness: 0.55, roughness: 0.4 }),
    );
    puente.position.y = h + 0.06;
    grupo.add(puente);
    [-0.38, 0.38].forEach((dz) => {
      const baranda = new THREE.Mesh(
        new THREE.BoxGeometry(r * 2 + 1, 0.06, 0.06),
        this._material(0xb6c6d4, { metalness: 0.6, roughness: 0.3 }),
      );
      baranda.position.set(0, h + 0.55, dz);
      grupo.add(baranda);
    });

    const columna = new THREE.Mesh(
      new THREE.CylinderGeometry(0.34, 0.34, h + 1.6, 16),
      this._material(0x6b7f90, { metalness: 0.6, roughness: 0.35 }),
    );
    columna.position.y = (h + 1.6) / 2;
    grupo.add(columna);
  }

  _tanque(grupo, u, ud, w, h, d) {
    const t = 0.3;
    const paredMat = this._material(new THREE.Color(u.color), {
      roughness: 0.6,
      metalness: 0.14,
    });
    const paredes = [
      [w, h, t, 0, h / 2, d / 2 - t / 2],
      [w, h, t, 0, h / 2, -d / 2 + t / 2],
      [t, h, d - 2 * t, w / 2 - t / 2, h / 2, 0],
      [t, h, d - 2 * t, -w / 2 + t / 2, h / 2, 0],
    ];
    paredes.forEach(([bw, bh, bd, px, py, pz]) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bd), paredMat);
      m.position.set(px, py, pz);
      grupo.add(m);
    });

    const fondo = new THREE.Mesh(
      new THREE.BoxGeometry(w, 0.28, d),
      this._material(0x22384c),
    );
    fondo.position.y = 0.14;
    grupo.add(fondo);

    const agua = new THREE.Mesh(
      new THREE.BoxGeometry(w - 0.75, h * 0.72, d - 0.75),
      this._agua(new THREE.Color(u.color)),
    );
    agua.position.y = 0.25 + (h * 0.72) / 2;
    grupo.add(agua);
    ud.waterMeshes.push(agua);

    // Pasarela lateral
    const pasarela = new THREE.Mesh(
      new THREE.BoxGeometry(w, 0.12, 1.1),
      this._material(0x8fa3b4, { metalness: 0.55, roughness: 0.42 }),
    );
    pasarela.position.set(0, h + 0.06, d / 2 + 0.55);
    grupo.add(pasarela);

    if (u.id === "aerobio") this._aireacion(grupo, ud, w, h, d);
    else this._mezclador(grupo, w, h, d);
  }

  _aireacion(grupo, ud, w, h, d) {
    const tuboMat = this._material(0x5b7285, { metalness: 0.65, roughness: 0.35 });
    for (let i = -2; i <= 2; i += 1) {
      const tubo = new THREE.Mesh(
        new THREE.CylinderGeometry(0.09, 0.09, d - 1.2, 8),
        tuboMat,
      );
      tubo.rotation.x = Math.PI / 2;
      tubo.position.set((i * w) / 6, 0.32, 0);
      grupo.add(tubo);
    }

    const count = 160;
    const posiciones = new Float32Array(count * 3);
    const velocidades = new Float32Array(count);
    for (let i = 0; i < count; i += 1) {
      posiciones[i * 3] = (Math.random() - 0.5) * (w - 1.4);
      posiciones[i * 3 + 1] = 0.3 + Math.random() * h * 0.65;
      posiciones[i * 3 + 2] = (Math.random() - 0.5) * (d - 1.4);
      velocidades[i] = 0.5 + Math.random() * 1.3;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(posiciones, 3));
    const puntos = new THREE.Points(
      geo,
      new THREE.PointsMaterial({
        color: 0xc9f2ff,
        size: 0.17,
        transparent: true,
        opacity: 0.8,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
    grupo.add(puntos);
    ud.bubbles = { puntos, posiciones, velocidades, top: h * 0.8, speed: 1 };
    this.bubbleSystems.push(ud.bubbles);
  }

  _mezclador(grupo, w, h, d) {
    const motor = new THREE.Mesh(
      new THREE.CylinderGeometry(0.32, 0.32, 1.4, 12),
      this._material(0xd0a24c, { metalness: 0.5, roughness: 0.4 }),
    );
    motor.position.set(w / 2 - 1.4, h + 0.7, 0);
    grupo.add(motor);
    const eje = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.08, h, 8),
      this._material(0x94a3b8, { metalness: 0.7, roughness: 0.3 }),
    );
    eje.position.set(w / 2 - 1.4, h / 2, 0);
    grupo.add(eje);
  }

  _canal(grupo, u, ud, w, h, d) {
    const paredMat = this._material(new THREE.Color(u.color), {
      roughness: 0.7,
      metalness: 0.12,
    });
    const fondo = new THREE.Mesh(
      new THREE.BoxGeometry(w, 0.25, d),
      this._material(0x20364a),
    );
    fondo.position.y = 0.12;
    grupo.add(fondo);
    [-d / 2 + 0.14, d / 2 - 0.14].forEach((pz) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.28), paredMat);
      m.position.set(0, h / 2, pz);
      grupo.add(m);
    });

    const agua = new THREE.Mesh(
      new THREE.BoxGeometry(w - 0.2, h * 0.74, d - 0.62),
      this._agua(new THREE.Color(u.color)),
    );
    agua.position.y = 0.25 + (h * 0.74) / 2;
    grupo.add(agua);
    ud.waterMeshes.push(agua);

    if (u.id === "rejillas") {
      for (let i = 0; i < 7; i += 1) {
        const barra = new THREE.Mesh(
          new THREE.BoxGeometry(0.09, h * 0.85, d - 0.5),
          this._material(0xb8c7d4, { metalness: 0.7, roughness: 0.28 }),
        );
        barra.position.set(-w / 2 + 1 + i * ((w - 2) / 6), h * 0.42, 0);
        grupo.add(barra);
      }
    }

    if (u.id === "desinfeccion") {
      const techo = new THREE.Mesh(
        new THREE.BoxGeometry(w + 0.4, 0.18, d + 0.4),
        this._material(0x14532d, { transparent: true, opacity: 0.55 }),
      );
      techo.position.y = h + 0.5;
      grupo.add(techo);
    }
  }

  _edificio(grupo, u, ud, w, h, d) {
    const cuerpo = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      this._material(new THREE.Color(u.color), { roughness: 0.82, metalness: 0.08 }),
    );
    cuerpo.position.y = h / 2;
    grupo.add(cuerpo);

    const techo = new THREE.Mesh(
      new THREE.BoxGeometry(w + 0.8, 0.3, d + 0.8),
      this._material(0x3f3f46, { roughness: 0.85 }),
    );
    techo.position.y = h + 0.15;
    grupo.add(techo);

    const ventanaMat = new THREE.MeshStandardMaterial({
      color: 0x0f2a3d,
      emissive: 0x38bdf8,
      emissiveIntensity: 0.8,
      roughness: 0.3,
    });
    for (let i = -1; i <= 1; i += 1) {
      const ventana = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.8, 0.08), ventanaMat);
      ventana.position.set(i * 3, h * 0.62, d / 2 + 0.02);
      grupo.add(ventana);
    }
    const puerta = new THREE.Mesh(
      new THREE.BoxGeometry(1.6, 2.2, 0.09),
      this._material(0x1f2937),
    );
    puerta.position.set(0, 1.1, d / 2 + 0.03);
    grupo.add(puerta);

    const chimenea = new THREE.Mesh(
      new THREE.CylinderGeometry(0.35, 0.35, 2.2, 10),
      this._material(0x52525b, { metalness: 0.5 }),
    );
    chimenea.position.set(w / 3, h + 1.2, -d / 4);
    grupo.add(chimenea);
  }

  _digestor(grupo, u, ud, w, h) {
    const r = w / 2;
    const cuerpoH = h * 0.76;
    const cuerpo = new THREE.Mesh(
      new THREE.CylinderGeometry(r, r, cuerpoH, 40),
      this._material(new THREE.Color(u.color), { roughness: 0.5, metalness: 0.25 }),
    );
    cuerpo.position.y = cuerpoH / 2;
    grupo.add(cuerpo);

    const domo = new THREE.Mesh(
      new THREE.SphereGeometry(r, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2),
      this._material(new THREE.Color(u.color).offsetHSL(0, 0, 0.05), {
        roughness: 0.45,
        metalness: 0.3,
      }),
    );
    domo.position.y = cuerpoH;
    grupo.add(domo);

    const cono = new THREE.Mesh(
      new THREE.ConeGeometry(r, 1.4, 40),
      this._material(0x4d5b42, { roughness: 0.8 }),
    );
    cono.rotation.x = Math.PI;
    cono.position.y = -0.7;
    grupo.add(cono);

    const escalera = new THREE.Mesh(
      new THREE.BoxGeometry(0.5, h + 1.2, 0.08),
      this._material(0x64748b, { metalness: 0.6 }),
    );
    escalera.position.set(r + 0.1, (h + 1.2) / 2, 0.6);
    grupo.add(escalera);

    const tubo = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.14, 3, 10),
      this._material(0x94a3b8, { metalness: 0.7, roughness: 0.3 }),
    );
    tubo.position.set(0, cuerpoH + r + 1.3, 0);
    grupo.add(tubo);

    const llama = new THREE.Mesh(
      new THREE.ConeGeometry(0.34, 1.1, 12),
      new THREE.MeshBasicMaterial({
        color: 0xffb347,
        transparent: true,
        opacity: 0.95,
      }),
    );
    llama.position.set(0, cuerpoH + r + 3.1, 0);
    grupo.add(llama);
    ud.flama = llama;

    const luz = new THREE.PointLight(0xffa94d, 8, 14, 2);
    luz.position.copy(llama.position);
    grupo.add(luz);
    ud.luzGas = luz;
  }

  // ------------------------------------------------------------------
  // Tuberías
  // ------------------------------------------------------------------
  _construirTuberias() {
    this.pipeGroup = new THREE.Group();
    this.scene.add(this.pipeGroup);

    CONEXIONES.forEach((c) => {
      const desde = this.units.get(c.from);
      const hasta = this.units.get(c.to);
      if (!desde || !hasta) return;
      const estilo = ESTILOS_TUBERIA[c.kind];

      const a = new THREE.Vector3(...desde.posicion);
      const b = new THREE.Vector3(...hasta.posicion);
      const dir = b.clone().sub(a);
      dir.y = 0;
      const largo = dir.length();
      if (largo < 0.01) return;
      dir.normalize();

      const halfA = Math.max(desde.dimensiones[0], desde.dimensiones[2]) * 0.42;
      const halfB = Math.max(hasta.dimensiones[0], hasta.dimensiones[2]) * 0.42;
      const altura = c.kind === "recirculacion" ? 1.7 : c.kind === "lodo" ? 0.85 : 0.65;

      const inicio = a.clone().addScaledVector(dir, halfA);
      inicio.y = altura;
      const fin = b.clone().addScaledVector(dir, -halfB);
      fin.y = altura;

      const puntos = [inicio];
      (c.via || []).forEach((p) => puntos.push(new THREE.Vector3(...p)));
      puntos.push(fin);
      if (puntos.length === 2) {
        const medio = inicio.clone().lerp(fin, 0.5);
        medio.y += 0.25;
        puntos.splice(1, 0, medio);
      }

      const curva = new THREE.CatmullRomCurve3(puntos, false, "catmullrom", 0.12);
      const segmentos = Math.max(24, Math.floor(largo * 1.4));
      const geo = new THREE.TubeGeometry(curva, segmentos, estilo.radio, 7, false);
      const mat = new THREE.MeshStandardMaterial({
        color: estilo.color,
        roughness: 0.42,
        metalness: 0.62,
        transparent: c.kind === "recirculacion" || c.kind === "rechazo",
        opacity: c.kind === "agua" || c.kind === "lodo" ? 1 : 0.72,
      });
      const tubo = new THREE.Mesh(geo, mat);
      tubo.castShadow = true;
      tubo.receiveShadow = true;
      this.pipeGroup.add(tubo);

      const dotGeo = new THREE.SphereGeometry(estilo.radio * 1.15, 7, 7);
      const dotMat = new THREE.MeshBasicMaterial({
        color: estilo.particula,
        transparent: true,
        opacity: 0.95,
      });
      for (let i = 0; i < estilo.puntos; i += 1) {
        const dot = new THREE.Mesh(dotGeo, dotMat);
        dot.userData.curva = curva;
        dot.userData.offset = i / estilo.puntos;
        dot.userData.velocidad = estilo.velocidad * (c.kind === "agua" ? 1.5 : 1);
        this.pipeGroup.add(dot);
        this.flowDots.push(dot);
      }
    });
  }

  // ------------------------------------------------------------------
  // Actualización de datos
  // ------------------------------------------------------------------
  update(resultado) {
    if (!resultado || !this.units.size) return;
    const etapas = new Map(resultado.etapas.map((e) => [e.id, e]));
    const reactores = new Map((resultado.reactores || []).map((r) => [r.id, r]));
    const lodos = new Map((resultado.tren_lodos?.etapas || []).map((e) => [e.id, e]));
    this.flowSpeed = Math.min(
      2.4,
      Math.max(0.5, Number(resultado.kpis?.caudal_tratado_m3_d || 9000) / 9000),
    );

    const aplicar = (id, calidad, texto, forzarColor = null) => {
      const ud = this.units.get(id);
      if (!ud) return;
      const cod = calidad?.dqo_mg_l ?? calidad?.cod ?? null;
      ud.cod = cod;
      if (forzarColor || cod !== null) {
        const color = forzarColor || (this.toggles.calidad ? qualityHex(cod) : ud.baseColor);
        ud.waterMeshes.forEach((m) => m.material.color.set(color));
      }
      if (ud.labelEl) {
        const small = ud.labelEl.querySelector("small");
        if (small) small.textContent = texto;
      }
    };

    aplicar("afluente", resultado.afluente, `DQO ${fmt(resultado.afluente.dqo_mg_l)} mg/L`);

    ["rejillas", "desarenador", "primario", "desinfeccion"].forEach((id) => {
      const etapa = etapas.get(id);
      if (etapa) {
        aplicar(id, etapa.salida, `DQO ${fmt(etapa.salida.dqo_mg_l)} · SST ${fmt(etapa.salida.sst_mg_l)}`);
      }
    });

    const biologico = etapas.get("biologico");
    if (biologico) {
      aplicar(
        "secundario",
        biologico.salida,
        `SST ${fmt(biologico.salida.sst_mg_l)} mg/L · η ${fmt(biologico.remocion.dqo_pct)} %`,
      );
    }

    [
      ["anaerobio", "anaerobio"],
      ["anoxico", "anoxico"],
      ["aerobio", "aerobio"],
    ].forEach(([idUnidad, idReactor]) => {
      const r = reactores.get(idReactor);
      if (!r) return;
      const cod = r.ss + r.xs + r.xbh + r.xba + r.xi;
      aplicar(
        idUnidad,
        { dqo_mg_l: cod },
        `SST ${fmt(r.sst)} · N-NH₄ ${fmt(r.nh4, 1)}`,
      );
    });

    aplicar("efluente", resultado.efluente, `DQO ${fmt(resultado.efluente.dqo_mg_l)} mg/L · SST ${fmt(resultado.efluente.sst_mg_l)}`);

    const esp = lodos.get("espesador");
    const dig = lodos.get("digestor");
    const des = lodos.get("deshidratacion");
    if (esp) {
      aplicar(
        "espesador",
        null,
        `${fmt(esp.entrada_kg_sst_d)} kg SST/d · ${fmt(esp.concentracion_pct, 1)} %`,
        0x8a6a3a,
      );
    }
    if (dig) {
      aplicar("digestor", null, `Biogás ${fmt(dig.biogas_m3_d)} m³/d`, 0x6b7a3a);
      const ud = this.units.get("digestor");
      if (ud?.flama) {
        const factor = Math.min(2.2, 0.7 + dig.biogas_m3_d / 700);
        ud.flama.scale.set(0.9 * factor, factor, 0.9 * factor);
        ud.luzGas.intensity = 4 + Math.min(18, dig.biogas_m3_d / 40);
      }
    }
    if (des) {
      aplicar("deshidratacion", null, `Torta ${fmt(des.torta_kg_sst_d)} kg SST/d`, 0x7c6a52);
    }

    const aire = Number(resultado.operacion_biologica?.aire_m3_d || 0);
    if (this.units.get("aerobio")?.bubbles) {
      this.units.get("aerobio").bubbles.speed = 0.55 + Math.min(1.6, aire / 60000);
    }

    if (this.selected) this.setSelected(this.selected);
  }

  // ------------------------------------------------------------------
  // Interacción
  // ------------------------------------------------------------------
  _enlazarEventos() {
    this._onPointerDown = (e) => {
      this.dragging = false;
      this._down = { x: e.clientX, y: e.clientY };
      this.renderer.domElement.style.cursor = "grabbing";
    };
    this._onPointerUp = (e) => {
      this.renderer.domElement.style.cursor = "grab";
      if (!this._down) return;
      const dx = e.clientX - this._down.x;
      const dy = e.clientY - this._down.y;
      if (dx * dx + dy * dy > 36) return;
      const id = this._pick(e);
      if (id) {
        this.setSelected(id);
        this.onSelect?.(id);
      }
    };
    this._onPointerMove = (e) => {
      if (e.buttons) return;
      const id = this._pick(e);
      this.renderer.domElement.style.cursor = id ? "pointer" : "grab";
    };
    this._onDoubleClick = (e) => {
      const id = this._pick(e);
      if (id) this.focusUnit(id);
    };

    const el = this.renderer.domElement;
    el.style.cursor = "grab";
    el.addEventListener("pointerdown", this._onPointerDown);
    el.addEventListener("pointerup", this._onPointerUp);
    el.addEventListener("pointermove", this._onPointerMove);
    el.addEventListener("dblclick", this._onDoubleClick);
  }

  _pick(event) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const objetivos = [...this.units.values()].map((u) => u.group);
    const hits = this.raycaster.intersectObjects(objetivos, true);
    for (const hit of hits) {
      let obj = hit.object;
      while (obj && !obj.userData.unitId) obj = obj.parent;
      if (obj?.userData.unitId) return obj.userData.unitId;
    }
    return null;
  }

  setSelected(id) {
    this.selected = id;
    this.units.forEach((ud) => {
      if (ud.labelEl) ud.labelEl.classList.toggle("is-selected", ud.id === id);
    });
    const ud = this.units.get(id);
    if (!ud) {
      this.ring.visible = false;
      return;
    }
    const escala = Math.max(ud.dimensiones[0], ud.dimensiones[2]) / 4.2;
    this.ring.position.set(ud.posicion[0], 0.08, ud.posicion[2]);
    this.ring.scale.setScalar(Math.max(1, escala));
    this.ring.visible = true;
  }

  setToggles(toggles) {
    this.toggles = { ...this.toggles, ...toggles };
    this.labelRenderer.domElement.style.display = this.toggles.etiquetas ? "" : "none";
    this.flowDots.forEach((d) => {
      d.visible = this.toggles.flujos;
    });
    if (!this.toggles.calidad) {
      this.units.forEach((ud) => {
        ud.waterMeshes.forEach((m) => m.material.color.set(ud.baseColor));
      });
    }
    this.units.forEach((ud) => ud.labelEl?.classList.toggle("is-hidden", false));
    this._labelFrame = 0;
  }

  /**
   * Oculta etiquetas que se solapan en pantalla. Se recalcula unas pocas veces
   * por segundo y prioriza la unidad seleccionada y los puntos clave del tren.
   */
  _actualizarEtiquetas() {
    if (!this.toggles.etiquetas) return;
    const prioridad = {
      afluente: 90,
      secundario: 85,
      aerobio: 80,
      digestor: 75,
      efluente: 70,
      primario: 65,
      anaerobio: 60,
      anoxico: 55,
      espesador: 50,
      deshidratacion: 45,
      desinfeccion: 40,
      rejillas: 35,
      desarenador: 30,
    };
    const lista = [...this.units.values()]
      .filter((ud) => ud.labelEl)
      .sort((a, b) => {
        if (a.id === this.selected) return -1;
        if (b.id === this.selected) return 1;
        return (prioridad[b.id] || 0) - (prioridad[a.id] || 0);
      });

    lista.forEach((ud) => ud.labelEl.classList.remove("is-hidden"));
    const ocupados = [];
    lista.forEach((ud) => {
      const rect = ud.labelEl.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const caja = {
        left: rect.left - 3,
        right: rect.right + 3,
        top: rect.top - 3,
        bottom: rect.bottom + 3,
      };
      const choque = ocupados.some(
        (o) =>
          !(
            caja.right < o.left ||
            caja.left > o.right ||
            caja.bottom < o.top ||
            caja.top > o.bottom
          ),
      );
      if (choque && ud.id !== this.selected) {
        ud.labelEl.classList.add("is-hidden");
      } else {
        ocupados.push(caja);
      }
    });
  }

  setView(nombre) {
    const vistas = {
      iso: { pos: [-4, 62, 60], target: [4, 0, 6] },
      aerea: { pos: [4, 88, 26], target: [4, 0, 5] },
      agua: { pos: [46, 24, 50], target: [12, 2, 0] },
      lodos: { pos: [2, 32, 54], target: [-5, 2, 15] },
    };
    const v = vistas[nombre] || vistas.iso;
    this._volar(v.pos, v.target);
  }

  focusUnit(id) {
    const ud = this.units.get(id);
    if (!ud) return;
    const [x, , z] = ud.posicion;
    const alto = Math.max(6, ud.dimensiones[1] + 4);
    this._volar([x - 12, alto + 7, z + 14], [x, 1.2, z], 0.75);
  }

  resetView() {
    this.setView("iso");
  }

  _volar(pos, target, duracion = 0.9) {
    this.tween = {
      fromPos: this.camera.position.clone(),
      toPos: new THREE.Vector3(...pos),
      fromTarget: this.controls.target.clone(),
      toTarget: new THREE.Vector3(...target),
      t: 0,
      duracion,
    };
  }

  // ------------------------------------------------------------------
  // Bucle
  // ------------------------------------------------------------------
  _animate() {
    this.raf = requestAnimationFrame(this._animate);
    const dt = Math.min(this.clock.getDelta(), 0.06);
    const t = this.clock.elapsedTime;

    if (this.tween) {
      this.tween.t += dt / this.tween.duracion;
      const k = Math.min(1, this.tween.t);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      this.camera.position.lerpVectors(this.tween.fromPos, this.tween.toPos, e);
      this.controls.target.lerpVectors(this.tween.fromTarget, this.tween.toTarget, e);
      if (k >= 1) this.tween = null;
    }

    if (this.toggles.rotacion && !this.tween) {
      const offset = this.camera.position.clone().sub(this.controls.target);
      offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), dt * 0.12);
      this.camera.position.copy(this.controls.target).add(offset);
    }

    this.controls.update();
    this.waterTexture.offset.x = (t * 0.012) % 1;
    this.waterTexture.offset.y = (t * 0.007) % 1;

    this.bubbleSystems.forEach((b) => {
      const pos = b.posiciones;
      for (let i = 1; i < pos.length; i += 3) {
        pos[i] += b.velocidades[(i - 1) / 3] * b.speed * dt;
        if (pos[i] > b.top) pos[i] = 0.32;
      }
      b.puntos.geometry.attributes.position.needsUpdate = true;
    });

    this.flowDots.forEach((dot) => {
      if (!dot.visible) return;
      const vel = dot.userData.velocidad * this.flowSpeed;
      const u = (dot.userData.offset + t * vel) % 1;
      dot.userData.curva.getPointAt(u, dot.position);
    });

    if (this.ring.visible) {
      this.ring.rotation.z += dt * 0.7;
      this.ring.material.opacity = 0.55 + 0.25 * Math.sin(t * 2.4);
    }

    if (this.units.get("digestor")?.flama) {
      const flama = this.units.get("digestor").flama;
      flama.material.opacity = 0.8 + 0.13 * Math.sin(t * 9);
    }

    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);

    this._labelFrame = (this._labelFrame || 0) + 1;
    if (this._labelFrame % 12 === 0) this._actualizarEtiquetas();
  }

  resize() {
    const w = this.container.clientWidth || 800;
    const h = this.container.clientHeight || 520;
    this.renderer.setSize(w, h, false);
    this.labelRenderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // ------------------------------------------------------------------
  // Limpieza
  // ------------------------------------------------------------------
  _disposeObject(root) {
    root.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        mats.forEach((m) => {
          if (m.map && m.map !== this.waterTexture) m.map.dispose();
          m.dispose();
        });
      }
    });
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObserver?.disconnect();
    const el = this.renderer.domElement;
    el.removeEventListener("pointerdown", this._onPointerDown);
    el.removeEventListener("pointerup", this._onPointerUp);
    el.removeEventListener("pointermove", this._onPointerMove);
    el.removeEventListener("dblclick", this._onDoubleClick);
    this.controls.dispose();
    this._limpiarUnidades();
    this._disposeObject(this.scene);
    this.waterTexture.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.labelRenderer.domElement.remove();
  }
}
