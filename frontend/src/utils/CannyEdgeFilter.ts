/**
 * WebGL-based Canny Edge Detection Filter
 * 
 * optimized for performance using a single pass shader where possible, 
 * or a minimal multi-pass setup.
 * 
 * For 'privacy' mode, we want a cool, stylized look. 
 * Standard Canny is: Grayscale -> Gaussian Blur -> Sobel -> Non-max suppression -> Hysteresis.
 * 
 * To keep it extremely fast (single pass preferred for video) and "cool" looking,
 * we will implement a "Sobel Edge Magnitude" filter with thresholding. 
 * This gives the "glowing edges" look which is perfect for privacy 
 * and much cheaper than full Canny (no non-max suppression needing neighbor lookups).
 */

export class CannyEdgeFilter {
    private canvas: HTMLCanvasElement;
    private gl: WebGLRenderingContext | null;
    private program: WebGLProgram | null = null;
    private positionLocation: number = 0;
    private texCoordLocation: number = 0;
    private positionBuffer: WebGLBuffer | null = null;
    private texCoordBuffer: WebGLBuffer | null = null;
    private texture: WebGLTexture | null = null;
    private width: number = 0;
    private height: number = 0;

    constructor() {
        this.canvas = document.createElement('canvas');
        this.gl = this.canvas.getContext('webgl', {
            preserveDrawingBuffer: true,
            alpha: false,
            antialias: false
        });

        if (!this.gl) {
            console.error('WebGL not supported, falling back to 2D canvas (not implemented)');
            return;
        }

        this.initShaders();
        this.initBuffers();
        this.initTexture();
    }

    private initShaders() {
        if (!this.gl) return;

        // Vertex Shader: Pass-through with texture coordinates
        const vsSource = `
      attribute vec2 a_position;
      attribute vec2 a_texCoord;
      varying vec2 v_texCoord;
      void main() {
        gl_Position = vec4(a_position, 0, 1);
        v_texCoord = a_texCoord;
      }
    `;

        // Fragment Shader: Edge Detection
        const fsSource = `
      precision mediump float;
      uniform sampler2D u_image;
      uniform vec2 u_textureSize;
      varying vec2 v_texCoord;

      void main() {
        vec2 onePixel = vec2(1.0, 1.0) / u_textureSize;
        
        // Sobel kernels
        // Gx: -1  0  1
        //     -2  0  2
        //     -1  0  1
        // Gy:  1  2  1
        //      0  0  0
        //     -1 -2 -1

        // Sample neighboring pixels
        float tl = dot(texture2D(u_image, v_texCoord + onePixel * vec2(-1, -1)).rgb, vec3(0.299, 0.587, 0.114));
        float tc = dot(texture2D(u_image, v_texCoord + onePixel * vec2( 0, -1)).rgb, vec3(0.299, 0.587, 0.114));
        float tr = dot(texture2D(u_image, v_texCoord + onePixel * vec2( 1, -1)).rgb, vec3(0.299, 0.587, 0.114));
        
        float ml = dot(texture2D(u_image, v_texCoord + onePixel * vec2(-1,  0)).rgb, vec3(0.299, 0.587, 0.114));
        float mr = dot(texture2D(u_image, v_texCoord + onePixel * vec2( 1,  0)).rgb, vec3(0.299, 0.587, 0.114));
        
        float bl = dot(texture2D(u_image, v_texCoord + onePixel * vec2(-1,  1)).rgb, vec3(0.299, 0.587, 0.114));
        float bc = dot(texture2D(u_image, v_texCoord + onePixel * vec2( 0,  1)).rgb, vec3(0.299, 0.587, 0.114));
        float br = dot(texture2D(u_image, v_texCoord + onePixel * vec2( 1,  1)).rgb, vec3(0.299, 0.587, 0.114));

        float x = -tl - 2.0*ml - bl + tr + 2.0*mr + br;
        float y =  tl + 2.0*tc + tr - bl - 2.0*bc - br;
        
        float magnitude = sqrt(x*x + y*y);

        // Thresholding for "Privacy" look (High contrast)
        // Tuning for facial features: 
        // 0.05 captures very subtle shadows (nose/cheek definition).
        // 0.15 ensures these weak edges become visible white lines.
        float threshold = 0.05; 
        float upper = 0.15;
        
        // Smooth step for nicer edges and hysteresis approximation
        float edge = smoothstep(threshold, upper, magnitude);
        
        // Invert: White edges on Black background is requested?
        // "only ‘canny edges’ is sent" -> usually implies black bg, white edges.
        
        gl_FragColor = vec4(vec3(edge), 1.0);
      }
    `;

        const vertexShader = this.createShader(this.gl.VERTEX_SHADER, vsSource);
        const fragmentShader = this.createShader(this.gl.FRAGMENT_SHADER, fsSource);

        if (!vertexShader || !fragmentShader) return;

        this.program = this.createProgram(vertexShader, fragmentShader);
        if (!this.program) return;

        this.positionLocation = this.gl.getAttribLocation(this.program, "a_position");
        this.texCoordLocation = this.gl.getAttribLocation(this.program, "a_texCoord");
    }

    private initBuffers() {
        if (!this.gl) return;

        // Full screen quad
        this.positionBuffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.positionBuffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array([
            -1.0, -1.0,
            1.0, -1.0,
            -1.0, 1.0,
            -1.0, 1.0,
            1.0, -1.0,
            1.0, 1.0,
        ]), this.gl.STATIC_DRAW);

        this.texCoordBuffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.texCoordBuffer);
        // Important: WebGL texture coordinates are flipped vertically compared to images sometimes,
        // but for videos generally 0,0 is bottom-left, while image top-left. 
        this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array([
            0.0, 1.0,
            1.0, 1.0,
            0.0, 0.0,
            0.0, 0.0,
            1.0, 1.0,
            1.0, 0.0,
        ]), this.gl.STATIC_DRAW);
    }

    private initTexture() {
        if (!this.gl) return;
        this.texture = this.gl.createTexture();
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture);

        // Set parameters so we can render any size image
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_S, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_WRAP_T, this.gl.CLAMP_TO_EDGE);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MIN_FILTER, this.gl.LINEAR);
        this.gl.texParameteri(this.gl.TEXTURE_2D, this.gl.TEXTURE_MAG_FILTER, this.gl.LINEAR);
    }

    process(source: HTMLVideoElement | HTMLCanvasElement): HTMLCanvasElement {
        if (!this.gl || !this.program || !source) return this.canvas;

        // Resize internal canvas if needed
        if (this.width !== source.width || this.height !== source.height ||
            // Handle video element dynamic size
            (source instanceof HTMLVideoElement && (this.width !== source.videoWidth || this.height !== source.videoHeight))) {

            this.width = source instanceof HTMLVideoElement ? source.videoWidth : source.width;
            this.height = source instanceof HTMLVideoElement ? source.videoHeight : source.height;
            this.canvas.width = this.width;
            this.canvas.height = this.height;
            this.gl.viewport(0, 0, this.width, this.height);
        }

        if (this.width === 0 || this.height === 0) return this.canvas;

        this.gl.useProgram(this.program);

        // Bind Position
        this.gl.enableVertexAttribArray(this.positionLocation);
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.positionBuffer);
        this.gl.vertexAttribPointer(this.positionLocation, 2, this.gl.FLOAT, false, 0, 0);

        // Bind TexCoord
        this.gl.enableVertexAttribArray(this.texCoordLocation);
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.texCoordBuffer);
        this.gl.vertexAttribPointer(this.texCoordLocation, 2, this.gl.FLOAT, false, 0, 0);

        // Upload Texture
        this.gl.bindTexture(this.gl.TEXTURE_2D, this.texture);
        this.gl.texImage2D(this.gl.TEXTURE_2D, 0, this.gl.RGBA, this.gl.RGBA, this.gl.UNSIGNED_BYTE, source);

        // Set Uniforms
        const textureSizeLocation = this.gl.getUniformLocation(this.program, "u_textureSize");
        this.gl.uniform2f(textureSizeLocation, this.width, this.height);

        // Draw
        this.gl.drawArrays(this.gl.TRIANGLES, 0, 6);

        return this.canvas;
    }

    private createShader(type: number, source: string): WebGLShader | null {
        if (!this.gl) return null;
        const shader = this.gl.createShader(type);
        if (!shader) return null;
        this.gl.shaderSource(shader, source);
        this.gl.compileShader(shader);
        if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
            console.error(this.gl.getShaderInfoLog(shader));
            this.gl.deleteShader(shader);
            return null;
        }
        return shader;
    }

    private createProgram(vertexShader: WebGLShader, fragmentShader: WebGLShader): WebGLProgram | null {
        if (!this.gl) return null;
        const program = this.gl.createProgram();
        if (!program) return null;
        this.gl.attachShader(program, vertexShader);
        this.gl.attachShader(program, fragmentShader);
        this.gl.linkProgram(program);
        if (!this.gl.getProgramParameter(program, this.gl.LINK_STATUS)) {
            console.error(this.gl.getProgramInfoLog(program));
            this.gl.deleteProgram(program);
            return null;
        }
        return program;
    }
}
