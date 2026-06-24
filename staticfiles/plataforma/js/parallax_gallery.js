document.addEventListener('DOMContentLoaded', function () {
  var DEPTH_LAYERS = 5;
  var IMAGES_PER_LAYER = 10;
  var MAX_WIDTH = 150;
  var MAX_HEIGHT = 150;

  var LAYER_CONFIG = [
    { scale: 1.5, speed: 48, opacity: 1.0 },
    { scale: 1.0, speed: 24, opacity: 0.85 },
    { scale: 0.8, speed: 18, opacity: 0.7 },
    { scale: 0.6, speed: 12, opacity: 0.55 },
    { scale: 0.5, speed: 9, opacity: 0.4 }
  ];

  var basePath = window.STATIC_ARTISTS || '/static/plataforma/img/artists/';
  var IMAGE_URLS = [
    basePath + 'shakira.jpg',
    basePath + 'michael_jackson.jpg',
    basePath + 'ed_sheeran.jpg',
    basePath + 'dua_lipa.jpg',
    basePath + 'maluma.jpg',
    basePath + 'rolling_stones.jpg',
    basePath + 'mana.jpg',
    basePath + 'gizmo_varillas.jpg',
    basePath + 'concert1.jpg',
    basePath + 'concert2.jpg',
    basePath + 'concert3.jpg',
    basePath + 'concert4.jpg',
    basePath + 'concert5.jpg',
    basePath + 'concert6.jpg',
    basePath + 'concert7.jpg',
    basePath + 'concert8.jpg',
    basePath + 'concert9.jpg',
    basePath + 'concert10.jpg',
    basePath + 'concert11.jpg',
    basePath + 'concert12.jpg',
    basePath + 'mj_tour.jpg',
    basePath + 'dua_future_nostalgia.jpg',
    basePath + 'rolling_stones2.jpg',
    basePath + 'ed_sheeran2.jpg',
    basePath + 'shakira2.jpg',
    basePath + 'maluma2.jpg',
    basePath + 'adele.jpg',
    basePath + 'beatles.jpg',
    basePath + 'bad_bunny_fb.jpg',
    basePath + 'mj_fb.jpg',
    basePath + 'julio_jaramillo.jpg'
  ];

  var container = document.getElementById('parallax-container');
  if (!container) return;

  container.style.width = (window.innerWidth * 0.45) + 'px';
  container.style.height = window.innerHeight + 'px';

  var W = container.offsetWidth;
  var H = container.offsetHeight;

  var renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(W, H);
  renderer.setClearColor(0x000000, 0);
  container.appendChild(renderer.domElement);

  var scene = new THREE.Scene();
  var camera = new THREE.OrthographicCamera(W / -2, W / 2, H / 2, H / -2, 1, 1000);
  camera.position.z = 500;

  var layers = [];
  var textureLoader = new THREE.TextureLoader();

  var loadedTextures = [];
  var loadCount = 0;

  function buildSceneFromTextures() {
    for (var li = 0; li < DEPTH_LAYERS; li++) {
      var cfg = LAYER_CONFIG[li];
      var sprites = [];

      for (var si = 0; si < IMAGES_PER_LAYER; si++) {
        var texIndex = (li * IMAGES_PER_LAYER + si) % loadedTextures.length;
        var tex = loadedTextures[texIndex];

        var w = MAX_WIDTH * cfg.scale;
        var h = MAX_HEIGHT * cfg.scale;

        var mat = new THREE.MeshBasicMaterial({
          map: tex,
          transparent: true,
          opacity: cfg.opacity,
          depthWrite: false
        });

        var geo = new THREE.PlaneGeometry(w, h);
        var mesh = new THREE.Mesh(geo, mat);

        var rx = (Math.random() - 0.5) * W * 1.8;
        var ry = (Math.random() - 0.5) * H * 1.8;
        mesh.position.set(rx, ry, li * 10);

        var vx = (Math.random() > 0.5 ? 1 : -1) * cfg.speed * (0.4 + Math.random() * 0.6);
        var vy = (Math.random() > 0.5 ? 1 : -1) * cfg.speed * 0.3 * (0.4 + Math.random() * 0.6);

        scene.add(mesh);
        sprites.push({ mesh: mesh, vx: vx, vy: vy, w: w, h: h, cfg: cfg });
      }

      layers.push(sprites);
    }
  }

  IMAGE_URLS.forEach(function (url) {
    textureLoader.load(
      url,
      function (tex) {
        loadedTextures.push(tex);
        loadCount++;
        if (loadCount === IMAGE_URLS.length) {
          buildSceneFromTextures();
          animate();
        }
      },
      undefined,
      function () {
        loadCount++;
        if (loadCount === IMAGE_URLS.length && loadedTextures.length > 0) {
          buildSceneFromTextures();
          animate();
        }
      }
    );
  });

  var dragActive = false;
  var lastX = 0;
  var dragVX = 0;
  var inertia = 0;
  var inertiaDecay = 0.95;
  var wheelBoost = 0;

  renderer.domElement.style.pointerEvents = 'none';

  var heroSection = container.closest('section') || document.body;
  heroSection.addEventListener('mousedown', function (e) {
    dragActive = true;
    lastX = e.clientX;
    dragVX = 0;
  });

  window.addEventListener('mousemove', function (e) {
    if (!dragActive) return;
    var dx = e.clientX - lastX;
    lastX = e.clientX;
    dragVX = dx * 2;
    inertia = dragVX;
  });

  window.addEventListener('mouseup', function () {
    dragActive = false;
  });

  window.addEventListener('wheel', function (e) {
    wheelBoost += e.deltaY * 0.3;
  }, { passive: true });

  var clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);

    var delta = clock.getDelta();
    var halfW = W / 2;
    var halfH = H / 2;

    if (!dragActive) {
      inertia *= inertiaDecay;
    }
    wheelBoost *= 0.9;

    for (var li = 0; li < layers.length; li++) {
      var depthFactor = 1 - li * 0.15;
      var sprites = layers[li];

      for (var si = 0; si < sprites.length; si++) {
        var s = sprites[si];

        var ix = inertia * depthFactor * 0.015;
        var wb = wheelBoost * depthFactor * 0.008;

        s.mesh.position.x += (s.vx * delta) + ix + wb;
        s.mesh.position.y += s.vy * delta;

        var halfSW = s.w / 2;
        var halfSH = s.h / 2;
        var limitX = halfW + halfSW;
        var limitY = halfH + halfSH;

        if (s.mesh.position.x > limitX) {
          s.mesh.position.x = -limitX;
        } else if (s.mesh.position.x < -limitX) {
          s.mesh.position.x = limitX;
        }

        if (s.mesh.position.y > limitY) {
          s.mesh.position.y = -limitY;
        } else if (s.mesh.position.y < -limitY) {
          s.mesh.position.y = limitY;
        }
      }
    }

    renderer.render(scene, camera);
  }

  window.addEventListener('resize', function () {
    container.style.width = (window.innerWidth * 0.45) + 'px';
    container.style.height = window.innerHeight + 'px';
    W = container.offsetWidth;
    H = container.offsetHeight;
    renderer.setSize(W, H);
    camera.left = W / -2;
    camera.right = W / 2;
    camera.top = H / 2;
    camera.bottom = H / -2;
    camera.updateProjectionMatrix();
  });
});
