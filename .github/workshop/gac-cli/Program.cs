using GmodAddonCompressor.DataContexts;
using GmodAddonCompressor.Systems;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

// Headless equivalent of pressing "Compress" in the GAC window.
// Every option maps 1:1 onto a GUI control; defaults match the GUI defaults
// (GmodAddonCompressor/DataContexts/MainWindowContext.cs).
//
// usage: gac-cli <directory> [--types vtf,png,jpg] [--resolution 2] [--target-width 1024]
//        [--target-height 1024] [--skip-width 0] [--skip-height 0] [--reduce-exactly-to-limits]
//        [--no-keep-aspect-ratio] [--imagemagick-vtf] [--wav-rate 44100] [--ffmpeg] [--lua-minimalistic]
//        [--verbose]

namespace GacCli
{
    internal static class Program
    {
        private static readonly string[] AllTypes = { "vtf", "png", "jpg", "wav", "mp3", "ogg", "lua" };

        private static async Task<int> Main(string[] args)
        {
            if (args.Length == 0 || args[0].StartsWith("-"))
            {
                Console.Error.WriteLine("usage: gac-cli <directory> [options]");
                return 2;
            }

            string directory = Path.GetFullPath(args[0]);
            if (!Directory.Exists(directory))
            {
                Console.Error.WriteLine($"Directory not found: {directory}");
                return 2;
            }

            var types = new HashSet<string> { "vtf", "png", "jpg" };
            int resolution = 2;
            int targetWidth = 1024;
            int targetHeight = 1024;
            int skipWidth = 0;
            int skipHeight = 0;
            bool reduceExactlyToLimits = false;
            bool keepAspectRatio = true;
            bool imageMagickVtf = false;
            int wavRate = 44100;
            bool ffmpeg = false;
            bool luaMinimalistic = false;
            bool verbose = false;

            for (int i = 1; i < args.Length; i++)
            {
                string Next() => i + 1 < args.Length ? args[++i] : throw new ArgumentException($"Missing value for {args[i]}");

                switch (args[i])
                {
                    case "--types":
                        types = Next().Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                            .Select(t => t.ToLowerInvariant()).ToHashSet();
                        var unknown = types.Except(AllTypes).ToList();
                        if (unknown.Count > 0) throw new ArgumentException($"Unknown types: {string.Join(",", unknown)}");
                        break;
                    case "--resolution": resolution = int.Parse(Next()); break;
                    case "--target-width": targetWidth = int.Parse(Next()); break;
                    case "--target-height": targetHeight = int.Parse(Next()); break;
                    case "--skip-width": skipWidth = int.Parse(Next()); break;
                    case "--skip-height": skipHeight = int.Parse(Next()); break;
                    case "--reduce-exactly-to-limits": reduceExactlyToLimits = true; break;
                    case "--no-keep-aspect-ratio": keepAspectRatio = false; break;
                    case "--imagemagick-vtf": imageMagickVtf = true; break;
                    case "--wav-rate": wavRate = int.Parse(Next()); break;
                    case "--ffmpeg": ffmpeg = true; break;
                    case "--lua-minimalistic": luaMinimalistic = true; break;
                    case "--verbose": verbose = true; break;
                    default: throw new ArgumentException($"Unknown option: {args[i]}");
                }
            }

            // Must be set before any GAC object is constructed: they grab their logger in field initializers.
            LogSystem.LoggerFactory = LoggerFactory.Create(builder => builder
                .AddSimpleConsole(o => { o.SingleLine = true; o.TimestampFormat = "HH:mm:ss "; })
                .SetMinimumLevel(verbose ? LogLevel.Debug : LogLevel.Information));

            AudioContext.SamplingFrequency = wavRate;
            AudioContext.UseFFMpegForCompress = ffmpeg;
            ImageContext.Resolution = resolution;
            ImageContext.TaargetWidth = targetWidth;
            ImageContext.TargetHeight = targetHeight;
            ImageContext.SkipWidth = skipWidth;
            ImageContext.SkipHeight = skipHeight;
            ImageContext.ReduceExactlyToLimits = reduceExactlyToLimits;
            ImageContext.KeepImageAspectRatio = keepAspectRatio;
            ImageContext.ImageMagickVTFCompress = imageMagickVtf;
            LuaContext.ChangeOriginalCodeToMinimalistic = luaMinimalistic;

            long sizeBefore = DirectorySize(directory);

            // GAC's VTFEdit converts foo.vtf to a scratch foo.png next to it and deletes any existing foo.png
            // first, so real PNGs that share a name with a VTF are moved aside while VTFs are processed.
            // VTFs and other types run in separate passes so PNGEdit never races VTFEdit on those files.
            if (types.Contains("vtf"))
            {
                string stash = Path.Combine(Path.GetTempPath(), "gac-png-stash-" + Guid.NewGuid().ToString("N"));
                var stashed = PngsShadowedByVtf(directory).ToList();
                foreach (string png in stashed)
                    MoveFile(png, Path.Combine(stash, Path.GetRelativePath(directory, png)));

                await RunPass(directory, new[] { "vtf" });
                CleanupVtfLeftovers(directory);

                foreach (string png in stashed)
                    MoveFile(Path.Combine(stash, Path.GetRelativePath(directory, png)), png);
                if (Directory.Exists(stash)) Directory.Delete(stash, true);
            }

            var otherTypes = types.Where(t => t != "vtf").ToArray();
            if (otherTypes.Length > 0)
            {
                await RunPass(directory, otherTypes);
                foreach (string leftover in Directory.EnumerateFiles(directory, "*____TEMP*", SearchOption.AllDirectories))
                    File.Delete(leftover);
            }

            long sizeAfter = DirectorySize(directory);
            Console.WriteLine($"GAC: done. {sizeBefore / 1048576.0:F1} MB -> {sizeAfter / 1048576.0:F1} MB");
            return 0;
        }

        private static async Task RunPass(string directory, string[] types)
        {
            Console.WriteLine($"GAC: compressing [{string.Join(",", types)}] in {directory}");

            var compressSystem = new CompressAddonSystem(directory);

            if (types.Contains("vtf")) compressSystem.IncludeVTF();
            if (types.Contains("wav")) compressSystem.IncludeWAV();
            if (types.Contains("mp3")) compressSystem.IncludeMP3();
            if (types.Contains("ogg")) compressSystem.IncludeOGG();
            if (types.Contains("jpg")) compressSystem.IncludeJPG();
            if (types.Contains("png")) compressSystem.IncludePNG();
            if (types.Contains("lua")) compressSystem.IncludeLUA();

            var completed = new TaskCompletionSource();
            int lastPercent = -1;
            compressSystem.e_ProgressChanged += (filePath, fileIndex, filesCount) =>
            {
                int percent = filesCount == 0 ? 100 : fileIndex * 100 / filesCount;
                if (percent / 5 != lastPercent / 5)
                {
                    lastPercent = percent;
                    Console.WriteLine($"GAC: {percent}% ({fileIndex}/{filesCount})");
                }
            };
            compressSystem.e_CompletedCompress += () => completed.TrySetResult();
            compressSystem.StartCompress();

            await completed.Task;
        }

        private static IEnumerable<string> PngsShadowedByVtf(string directory) =>
            Directory.EnumerateFiles(directory, "*.png", SearchOption.AllDirectories)
                .Where(png => File.Exists(Path.ChangeExtension(png, ".vtf")));

        // GAC gives up on a file after 2 minutes without cleaning up. Put the original VTF back
        // (it's kept as foo.vtf____TEMP.vtf) and remove the scratch PNG.
        private static void CleanupVtfLeftovers(string directory)
        {
            foreach (string temp in Directory.EnumerateFiles(directory, "*.vtf____TEMP.vtf", SearchOption.AllDirectories))
            {
                string vtf = temp.Substring(0, temp.Length - "____TEMP.vtf".Length);
                Console.WriteLine($"GAC: restoring original after timeout: {Path.GetRelativePath(directory, vtf)}");
                File.Copy(temp, vtf, true);
                File.Delete(temp);
            }

            foreach (string png in PngsShadowedByVtf(directory).ToList())
                File.Delete(png);
        }

        private static void MoveFile(string from, string to)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(to)!);
            File.Move(from, to, true);
        }

        private static long DirectorySize(string directory) =>
            new DirectoryInfo(directory).EnumerateFiles("*", SearchOption.AllDirectories).Sum(f => f.Length);
    }
}
