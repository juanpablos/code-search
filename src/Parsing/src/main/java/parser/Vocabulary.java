package parser;

import com.github.javaparser.ParseProblemException;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

import static java.util.Map.Entry.comparingByValue;
import static java.util.stream.Collectors.toMap;
import static parser.MethodCodeParser.parseMethod;

public class Vocabulary {
    private static String workingPath = "../data/java_corpus/";
    private static String nameVocab = workingPath + "nameVocab.csv";
    private static String apiVocab = workingPath + "apiVocab.csv";
    private static String tokenVocab = workingPath + "tokenVocab.csv";
    private static String commentVocab = workingPath + "commentVocab.csv";

    public static void main(String[] args) throws IOException {
        generateVocabulary(args[0]);
    }

    public static void generateVocabulary(String mainFile) throws IOException {
        generateVocabulary(mainFile, false);
    }

    public static void generateVocabulary(String mainFile, boolean hasHeader) throws IOException {
        Map<String, Integer> names = new HashMap<>();
        Map<String, Integer> apis = new HashMap<>();
        Map<String, Integer> tokens = new HashMap<>();
        Map<String, Integer> comments = new HashMap<>();

        int progress = 0;
        int ex = 0;
        CSVFormat format;
        if (hasHeader) {
            format = CSVFormat.DEFAULT
                    .withFirstRecordAsHeader()
                    .withIgnoreHeaderCase()
                    .withTrim();
        } else {
            format = CSVFormat.DEFAULT
                    .withHeader("comment", "code")
                    .withIgnoreHeaderCase()
                    .withTrim();
        }
        try (Reader reader = Files.newBufferedReader(Paths.get(workingPath + mainFile));
             CSVParser csvParser = new CSVParser(reader, format)) {

            System.out.println("Parsing Methods");
            for (CSVRecord line : csvParser) {

                if (progress % 333693 == 0) {
                    System.out.println("Progress: " + progress / 333693 + "%");
                    if (progress > 10)
                        break;
                }

                try {
                    MethodContainer mc = parseMethod(line.get("code"));

                    for (String name : mc.getNameTokens()) {
                        if (!(name.equals(" ") || name.equals("_"))) {
                            names.merge(name, 1, (oldValue, one) -> oldValue + one);
                        }
                    }
                    for (String api : mc.getApiCalls()) {
                        if (!(api.equals(" ") || api.equals("_"))) {
                            apis.merge(api, 1, (oldValue, one) -> oldValue + one);
                        }
                    }
                    for (String token : mc.getBodyTokens()) {
                        if (!(token.equals(" ") || token.equals("_"))) {
                            tokens.merge(token, 1, (oldValue, one) -> oldValue + one);
                        }
                    }
                    for (String word : line.get("doc").toLowerCase().split("\\P{L}+")) {
                        if (!(word.equals("") || word.equals(" ") || word.equals("_"))) {
                            comments.merge(word, 1, (oldValue, one) -> oldValue + one);
                        }
                    }
                } catch (ParseProblemException e) {
                    ex++;
                }

                progress++;
            }
        }

        System.out.println(ex + " parsing exceptions");

        System.out.println("Writing Vocabularies");

        int i = 2;
        try (Writer writer = Files.newBufferedWriter(Paths.get(nameVocab));
             CSVPrinter nameWriter = new CSVPrinter(writer, CSVFormat.DEFAULT
                     .withHeader("word", "id", "occ"))) {

            System.out.println("Writing Names");
            for (Map.Entry<String, Integer> pair : sortedMap(names).entrySet()) {
                nameWriter.printRecord(pair.getKey(), i++, pair.getValue());
            }
        }

        i = 2;
        try (Writer writer = Files.newBufferedWriter(Paths.get(apiVocab));
             CSVPrinter apiWriter = new CSVPrinter(writer, CSVFormat.DEFAULT
                     .withHeader("word", "id", "occ"))) {

            System.out.println("Writing APIs");
            for (Map.Entry<String, Integer> pair : sortedMap(apis).entrySet()) {
                apiWriter.printRecord(pair.getKey(), i++, pair.getValue());
            }
        }

        i = 2;
        try (Writer writer = Files.newBufferedWriter(Paths.get(tokenVocab));
             CSVPrinter tokenWriter = new CSVPrinter(writer, CSVFormat.DEFAULT
                     .withHeader("word", "id", "occ"))) {

            System.out.println("Writing Tokens");
            for (Map.Entry<String, Integer> pair : sortedMap(tokens).entrySet()) {
                tokenWriter.printRecord(pair.getKey(), i++, pair.getValue());
            }
        }

        i = 2;
        try (Writer writer = Files.newBufferedWriter(Paths.get(commentVocab));
             CSVPrinter commentWriter = new CSVPrinter(writer, CSVFormat.DEFAULT
                     .withHeader("word", "id", "occ"))) {

            System.out.println("Writing Comments");
            for (Map.Entry<String, Integer> pair : sortedMap(comments).entrySet()) {
                commentWriter.printRecord(pair.getKey(), i++, pair.getValue());
            }
        }

        System.out.println("End");
    }

    private static Map<String, Integer> sortedMap(Map<String, Integer> collection) {
        return collection
                .entrySet()
                .stream()
                .sorted(Collections.reverseOrder(comparingByValue()))
                .collect(toMap(
                        Map.Entry::getKey,
                        Map.Entry::getValue,
                        (e1, e2) -> e2,
                        LinkedHashMap::new
                ));
    }
}
